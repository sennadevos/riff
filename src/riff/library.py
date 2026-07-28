"""View and delete files already in the music library.

Deliberately minimal: list what's there and delete a file. No rename, no tag
editing, no upload. The library is a flat directory (riff's downloads write
directly into it, no subfolders), so listing is non-recursive.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mutagen import File as MutagenFile

_AUDIO_EXTS = {".mp3", ".flac", ".opus", ".m4a", ".ogg", ".wav"}


def _read_tags(path: Path) -> tuple[str, str]:
    """Best-effort (title, artist) from tags, falling back to the filename."""
    try:
        audio = MutagenFile(path, easy=True)
    except Exception:
        audio = None

    title = ""
    artist = ""
    if audio is not None:
        title = (audio.get("title") or [""])[0]
        artist = (audio.get("artist") or [""])[0]

    return title or path.stem, artist


def list_tracks(music_dir: str | Path) -> list[dict[str, Any]]:
    base = Path(music_dir).expanduser().resolve()
    if not base.is_dir():
        return []

    tracks = []
    for entry in os.scandir(base):
        if not entry.is_file():
            continue
        path = Path(entry.path)
        if path.suffix.lower() not in _AUDIO_EXTS:
            continue
        title, artist = _read_tags(path)
        stat = entry.stat()
        tracks.append({
            "filename": path.name,
            "title": title,
            "artist": artist,
            "size": stat.st_size,
            "mtime": stat.st_mtime,
        })

    tracks.sort(key=lambda t: t["mtime"], reverse=True)
    return tracks


def delete_track(music_dir: str | Path, filename: str) -> None:
    base = Path(music_dir).expanduser().resolve()
    target = (base / filename).resolve()

    if target.parent != base:
        raise ValueError("invalid filename")
    if not target.is_file():
        raise FileNotFoundError(filename)

    target.unlink()
