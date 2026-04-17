from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.config import get_settings
from app.models import StreamEvent, SummarizeRequest
from app.summarizer import SummarizationService

app = FastAPI(title="Real-Time Web Summarizer API", version="0.1.0")
settings = get_settings()
service = SummarizationService(settings=settings)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/ws/summarize")
async def ws_summarize(websocket: WebSocket) -> None:
    await websocket.accept()

    async def emit(event: str, message: str, data: dict) -> None:
        payload = StreamEvent(event=event, message=message, data=data)
        await websocket.send_json(payload.model_dump())

    try:
        raw = await websocket.receive_json()
        req = SummarizeRequest.model_validate(raw)
        await emit("progress", "Request accepted", {})
        result = await service.summarize(req=req, emit=emit)
        await emit("done", "Summarization complete", {"summary": result})
    except WebSocketDisconnect:
        return
    except Exception as exc:  # pragma: no cover
        await emit("error", "Summarization failed", {"reason": str(exc)})
    finally:
        await websocket.close()
