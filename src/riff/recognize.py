"""Identify library tracks via Shazam's audio recognition, using shazamio.

Manually triggered only (a library scan, not a watcher) — this module never
writes anything; see :mod:`riff.tagger` for applying identified tags.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shazamio import Shazam

_shazam: Shazam | None = None


def _get_shazam() -> Shazam:
    global _shazam
    if _shazam is None:
        _shazam = Shazam()
    return _shazam


async def identify(path: str | Path) -> dict[str, Any] | None:
    """Recognize one audio file. Returns None if there's no confident match."""
    try:
        out = await _get_shazam().recognize(str(path))
    except Exception:
        return None

    track = out.get("track") if out else None
    if not track:
        return None

    images = track.get("images") or {}
    cover_art_url = images.get("coverarthq") or images.get("coverart") or ""

    album = ""
    year = ""
    for section in track.get("sections") or []:
        if section.get("type") == "SONG":
            for entry in section.get("metadata") or []:
                if entry.get("title") == "Album":
                    album = entry.get("text", "")
                elif entry.get("title") == "Released":
                    year = entry.get("text", "")
            break

    return {
        "title": track.get("title", ""),
        "artist": track.get("subtitle", ""),
        "album": album,
        "year": year,
        "genre": (track.get("genres") or {}).get("primary", ""),
        "cover_art_url": cover_art_url,
    }
