# Real-Time Web Summarizer Extension with OpenAI API

A clean, scalable starter project for a browser extension that summarizes any open page in near real time using a Python backend powered by OpenAI API.

## Architecture

- `extension/`: Manifest V3 extension (popup + content extraction + background bridge).
- `backend/`: FastAPI WebSocket service that orchestrates chunking, parallel map summaries, and final reduce summary.
- `backend/app/qwen_agent_client.py`: OpenAI client wrapper for model calls.
- `backend/app/summarizer.py`: Latency and reliability focused summarization pipeline.

## Why this design

- Low latency: parallel chunk summarization with bounded concurrency.
- Reliable: retries with exponential backoff and graceful per-chunk fallback.
- Scalable: stateless API, async I/O, and clear layer separation.
- Clean: typed request/response contracts and single-responsibility modules.

## Step-by-step setup

### 1) Create and activate Python environment

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```bash
pip install -e .
```

### 3) Configure environment

Copy `backend/.env.example` to `backend/.env` and set:

- `OPENAI_API_KEY`: your OpenAI API key.
- Optional tuning vars for model, chunking, concurrency, and timeouts.

### 4) Run backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

### 5) Load extension

1. Open browser extensions page (`chrome://extensions` or `edge://extensions`).
2. Enable **Developer mode**.
3. Click **Load unpacked** and choose the `extension/` folder.
4. Open any web page and click the extension icon.
5. Click **Summarize this page**.

## Runtime flow

1. `content.js` extracts clean text from the active tab.
2. `popup.js` opens a WebSocket to backend and sends extracted content.
3. Backend splits content into chunks and summarizes chunks in parallel.
4. Backend streams chunk-level progress + partial output to popup.
5. Backend sends final reduced summary with key points and action items.

## Reliability and latency guardrails

- Max content size clamp to avoid pathological pages.
- Adaptive chunking for stable token budget.
- Bounded parallelism to protect provider/API.
- Retry policy for transient network/provider failures.
- Fallback partial output even if one chunk fails.
- Timeout caps to avoid hanging requests.

## Next hardening steps

- Add Redis caching keyed by content hash.
- Add per-IP/token rate limiting and auth token for extension clients.
- Persist summary jobs for audit/analytics.
- Add OpenTelemetry tracing for chunk latency and model timing.
- Add load tests (`k6`) and CI checks.

## Project layout

```text
AGENTIC/
  README.md
  backend/
    pyproject.toml
    .env.example
    app/
      __init__.py
      config.py
      models.py
      qwen_agent_client.py
      summarizer.py
      main.py
  extension/
    manifest.json
    src/
      background.js
      content.js
      popup.html
      popup.js
      styles.css
```
