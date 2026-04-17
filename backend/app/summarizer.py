from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from typing import Awaitable, Callable

from app.config import Settings
from app.models import SummarizeRequest
from app.qwen_agent_client import OpenAIClient

EventCallback = Callable[[str, str, dict], Awaitable[None]]


@dataclass
class ChunkResult:
    index: int
    summary: str
    ok: bool = True


class SummarizationService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAIClient(settings=settings)
        self._cache: dict[str, str] = {}

    def _sanitize(self, text: str) -> str:
        collapsed = " ".join(text.split())
        return collapsed[: self.settings.max_input_chars]

    def _chunk_text(self, text: str) -> list[str]:
        chunks: list[str] = []
        step = max(200, self.settings.chunk_chars - self.settings.chunk_overlap)
        for start in range(0, len(text), step):
            chunks.append(text[start : start + self.settings.chunk_chars])
            if start + self.settings.chunk_chars >= len(text):
                break
        return chunks

    def _mode_instruction(self, mode: str) -> str:
        if mode == "detailed":
            return "Return a detailed summary with sections and key evidence."
        if mode == "bullet":
            return "Return concise bullet points only."
        return "Return a concise summary in 5-8 sentences."

    async def summarize(self, req: SummarizeRequest, emit: EventCallback) -> str:
        clean_text = self._sanitize(req.content)
        cache_key = hashlib.sha256(f"{req.mode}:{clean_text}".encode("utf-8")).hexdigest()
        if cache_key in self._cache:
            await emit("progress", "Cache hit", {"source": "memory-cache"})
            return self._cache[cache_key]

        chunks = self._chunk_text(clean_text)
        await emit("progress", "Started summarization", {"chunks": len(chunks)})
        semaphore = asyncio.Semaphore(self.settings.max_parallel_chunks)
        mode_instruction = self._mode_instruction(req.mode)

        if len(chunks) == 1:
            await emit("progress", "Single chunk detected, using one-pass summary", {})
            system = (
                "You are a reliable web content summarization assistant. "
                "Stay factual and avoid hallucinations."
            )
            user = (
                f"Page title: {req.title}\n"
                f"Page URL: {req.url}\n"
                f"Task: Summarize the page. {mode_instruction}\n\n"
                f"Content:\n{chunks[0]}"
            )
            final_summary = await self.client.summarize_text(system, user)
            self._cache[cache_key] = final_summary
            return final_summary

        async def summarize_chunk(index: int, chunk: str) -> ChunkResult:
            system = (
                "You are a reliable web content summarization assistant. "
                "Stay factual and avoid hallucinations."
            )
            user = (
                f"Page title: {req.title}\n"
                f"Page URL: {req.url}\n"
                f"Task: Summarize chunk {index + 1}/{len(chunks)}. {mode_instruction}\n\n"
                f"Chunk content:\n{chunk}"
            )
            async with semaphore:
                try:
                    summary = await self.client.summarize_text(system, user)
                    await emit(
                        "partial",
                        f"Chunk {index + 1} summarized",
                        {"chunk_index": index, "text": summary},
                    )
                    return ChunkResult(index=index, summary=summary, ok=True)
                except Exception as exc:  # pragma: no cover
                    fallback = (
                        f"[Chunk {index + 1} failed after retries. "
                        f"Reason: {type(exc).__name__}]"
                    )
                    await emit(
                        "partial",
                        f"Chunk {index + 1} fallback",
                        {"chunk_index": index, "text": fallback},
                    )
                    return ChunkResult(index=index, summary=fallback, ok=False)

        chunk_results = await asyncio.gather(
            *[summarize_chunk(i, c) for i, c in enumerate(chunks)]
        )
        chunk_results.sort(key=lambda x: x.index)
        successful = [result for result in chunk_results if result.ok]
        if not successful:
            return (
                "Unable to summarize right now because the model API is rate-limited. "
                "Please wait 1-2 minutes and try again, or reduce request rate."
            )
        if len(successful) == 1:
            self._cache[cache_key] = successful[0].summary
            return successful[0].summary

        stitched = "\n".join(result.summary for result in successful)

        await emit("progress", "Reducing chunk summaries", {})
        final_system = (
            "You are a senior analyst. Merge chunk summaries into one coherent output. "
            "Keep only claims supported by chunk text."
        )
        final_user = (
            f"Page title: {req.title}\n"
            f"Page URL: {req.url}\n"
            f"Output style: {mode_instruction}\n\n"
            f"Chunk summaries:\n{stitched}\n\n"
            "Provide final output with:\n"
            "1) Main summary\n"
            "2) Key points\n"
            "3) Actionable takeaways"
        )
        final_summary = await self.client.summarize_text(final_system, final_user)
        self._cache[cache_key] = final_summary
        return final_summary
