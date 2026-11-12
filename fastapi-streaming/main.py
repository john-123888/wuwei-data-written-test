"""
Wuwei Data written test - Streaming API demo with FastAPI

Run:
    pip install fastapi uvicorn
    uvicorn main:app --reload --port 8000

Endpoints
---------
GET /            -> simple JSON info page
GET /stream      -> server-side streaming (chunked text, StreamingResponse)
GET /stream-sse  -> Server-Sent Events (text/event-stream)
GET /stream-lines?count=5 -> streams JSON lines (application/x-ndjson)
"""

import asyncio
import json
import time

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI(
    title="Streaming API Demo",
    description="Wuwei Data written test - FastAPI streaming demo",
    version="1.0.0",
)


@app.get("/")
def index() -> dict:
    return {
        "message": "FastAPI streaming demo",
        "endpoints": {
            "/stream": "chunked text streaming (StreamingResponse)",
            "/stream-sse": "Server-Sent Events",
            "/stream-lines": "JSON lines streaming (NDJSON), query param: count (default 5)",
        },
    }


@app.get("/stream")
def stream() -> StreamingResponse:
    """Streams 10 chunks of text with a 0.5s delay between chunks."""

    def text_generator():
        for i in range(1, 11):
            yield f"chunk {i}: Hello World\n"
            time.sleep(0.5)  # simulate slow work / downstream latency

    return StreamingResponse(text_generator(), media_type="text/plain")


@app.get("/stream-sse")
async def stream_sse() -> StreamingResponse:
    """Server-Sent Events stream: one event per second, 10 events in total."""

    async def sse_generator():
        for i in range(1, 11):
            payload = {"seq": i, "message": "Hello World", "ts": time.time()}
            yield f"id: {i}\nevent: message\ndata: {json.dumps(payload)}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/stream-lines")
async def stream_lines(count: int = 5) -> StreamingResponse:
    """Streams NDJSON: one JSON object per line, useful for LLM-style token streaming."""
    count = max(1, min(count, 50))  # clamp 1..50

    async def lines_generator():
        for i in range(1, count + 1):
            yield json.dumps({"index": i, "token": f"Hello-{i}"}) + "\n"
            await asyncio.sleep(0.3)

    return StreamingResponse(lines_generator(), media_type="application/x-ndjson")
