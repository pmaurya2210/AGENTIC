from __future__ import annotations

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import Settings


class OpenAIClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.openai_base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }

    async def summarize_text(self, system_prompt: str, user_prompt: str) -> str:
        @retry(
            retry=retry_if_exception_type(Exception),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            stop=stop_after_attempt(self.settings.openai_max_retries),
            reraise=True,
        )
        async def _call() -> str:
            payload = {
                "model": self.settings.openai_model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
            timeout = self.settings.openai_call_timeout_seconds
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise RuntimeError("Empty response from OpenAI API")
            content = choices[0].get("message", {}).get("content", "")
            return str(content).strip()

        return await _call()
