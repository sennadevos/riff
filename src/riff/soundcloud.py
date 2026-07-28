"""yt-dlp wrapper for searching SoundCloud.

Not every track is on YouTube Music; SoundCloud fills gaps. Downloading a
SoundCloud URL already works unchanged via :mod:`riff.download` (it just hands
any URL to yt-dlp) — this module only adds search.
"""

from __future__ import annotations

from typing import Any

import yt_dlp


def _format_duration(seconds: float | int | None) -> str:
    if not seconds:
        return ""
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


def search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"scsearch{limit}:{query}", download=False)

    entries = (info or {}).get("entries") or []
    results = []
    for e in entries:
        if not e:
            continue
        results.append({
            "title": e.get("title", ""),
            "artist": e.get("uploader", ""),
            "duration": _format_duration(e.get("duration")),
            "thumbnail": e.get("thumbnail", ""),
            "url": e.get("webpage_url") or e.get("url", ""),
        })
    return results[:limit]
