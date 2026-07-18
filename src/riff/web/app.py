"""FastAPI app serving a one-page web version of riff.

Reuses :mod:`riff.search` and :mod:`riff.download` unchanged. Search is a plain
JSON endpoint; downloads stream live progress to the browser as Server-Sent
Events, driven by yt-dlp's ``progress_callback`` (the same hook the CLI uses).
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from riff import download as riff_download
from riff import search as riff_search


# Where downloads are saved. Point this at whatever folder your music library
# or player watches. Overridable via the RIFF_MUSIC_DIR env var or `riff serve -m`.
MUSIC_DIR = os.environ.get("RIFF_MUSIC_DIR", "~/Music")
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="riff web", docs_url=None, redoc_url=None)


def _result_url(r: dict[str, Any]) -> str:
    """Build a YouTube Music URL from a search result (mirrors cli.py)."""
    if r.get("videoId"):
        return f"https://music.youtube.com/watch?v={r['videoId']}"
    if r.get("playlistId"):
        return f"https://music.youtube.com/playlist?list={r['playlistId']}"
    if r.get("browseId"):
        return f"https://music.youtube.com/browse/{r['browseId']}"
    return ""


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "music_dir": str(Path(MUSIC_DIR).expanduser())}


@app.get("/api/search")
def api_search(q: str, type: str = "song", limit: int = 10) -> JSONResponse:
    if not q.strip():
        return JSONResponse([])
    if type not in ("song", "video", "album", "artist", "playlist"):
        type = "song"
    try:
        results = riff_search.search(q, result_type=type, limit=limit)
    except Exception as e:  # surface upstream errors to the page
        return JSONResponse({"error": str(e)}, status_code=502)
    for r in results:
        r["url"] = _result_url(r)
    return JSONResponse(results)


@app.post("/api/download")
async def api_download(req: Request) -> StreamingResponse:
    body = await req.json()
    url = (body.get("url") or "").strip()
    fmt = body.get("format", "best")
    is_playlist = bool(body.get("playlist"))

    async def event_stream():
        if not url:
            yield _sse("error", {"error": "missing url"})
            return

        events: queue.Queue = queue.Queue()
        loop = asyncio.get_event_loop()

        def progress_hook(d: dict[str, Any]) -> None:
            # Runs in the worker thread; just enqueue a compact snapshot.
            try:
                status = d.get("status")
                info: dict[str, Any] = {
                    "status": status,
                    "filename": Path(d.get("filename", "")).name,
                }
                if status == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    downloaded = d.get("downloaded_bytes", 0)
                    if total:
                        info["percent"] = round(downloaded / total * 100, 1)
                    info["speed"] = d.get("speed")
                events.put(("progress", info))
            except Exception:
                pass

        def worker() -> None:
            try:
                if is_playlist:
                    res = riff_download.download_playlist(
                        url, output_dir=MUSIC_DIR, fmt=fmt, progress_callback=progress_hook
                    )
                else:
                    res = riff_download.download_audio(
                        url, output_dir=MUSIC_DIR, fmt=fmt, progress_callback=progress_hook
                    )
                events.put(("done", res))
            except Exception as e:
                events.put(("error", {"error": str(e)}))
            finally:
                events.put(("__end__", None))

        threading.Thread(target=worker, daemon=True).start()

        while True:
            event, data = await loop.run_in_executor(None, events.get)
            if event == "__end__":
                break
            yield _sse(event, data)

    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
