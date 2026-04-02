"""yt-dlp wrapper for downloading audio."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import yt_dlp


_FORMAT_MAP: dict[str, dict[str, Any]] = {
    "best": {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "opus",
            "preferredquality": "0",
        }],
    },
    "opus": {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "opus",
            "preferredquality": "0",
        }],
    },
    "mp3": {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }],
    },
    "flac": {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "flac",
            "preferredquality": "0",
        }],
    },
}

_OUTPUT_TEMPLATE = "%(artist,uploader)s - %(title)s.%(ext)s"


def _build_opts(
    output_dir: str | Path,
    fmt: str,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    fmt_opts = _FORMAT_MAP.get(fmt, _FORMAT_MAP["best"])

    opts: dict[str, Any] = {
        "format": fmt_opts["format"],
        "outtmpl": str(output_dir / _OUTPUT_TEMPLATE),
        "postprocessors": [
            *fmt_opts["postprocessors"],
            {"key": "EmbedThumbnail"},
            {"key": "FFmpegMetadata"},
        ],
        "writethumbnail": True,
        "quiet": True,
        "no_warnings": True,
    }

    if progress_callback:
        opts["progress_hooks"] = [progress_callback]

    return opts


def download_audio(
    url: str,
    output_dir: str | Path = "~/Music",
    fmt: str = "best",
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    opts = _build_opts(output_dir, fmt, progress_callback)

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

    if info is None:
        return {"error": "Failed to extract info"}

    return {
        "title": info.get("title", ""),
        "artist": info.get("artist") or info.get("uploader", ""),
        "path": str(Path(output_dir).expanduser().resolve()),
        "url": url,
    }


def download_playlist(
    url: str,
    output_dir: str | Path = "~/Music",
    fmt: str = "best",
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    opts = _build_opts(output_dir, fmt, progress_callback)

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

    if info is None:
        return []

    results = []
    for entry in info.get("entries", []):
        if entry is None:
            continue
        results.append({
            "title": entry.get("title", ""),
            "artist": entry.get("artist") or entry.get("uploader", ""),
            "path": str(Path(output_dir).expanduser().resolve()),
            "url": entry.get("webpage_url", ""),
        })

    return results
