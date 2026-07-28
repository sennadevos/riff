"""Write identified tags (and cover art) onto a library file.

Only ever called explicitly per-track from the web UI's "Apply" button —
never automatically. See :mod:`riff.recognize` for identification.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import requests
from mutagen import File as MutagenFile
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, ID3, ID3NoHeaderError
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

_EASY_FIELDS = {
    "title": "title",
    "artist": "artist",
    "album": "album",
    "year": "date",
    "genre": "genre",
}


def _write_easy_tags(path: Path, tags: dict[str, Any]) -> None:
    audio = MutagenFile(path, easy=True)
    if audio is None:
        return
    for key, easy_key in _EASY_FIELDS.items():
        value = tags.get(key)
        if value:
            audio[easy_key] = str(value)
    audio.save()


def _embed_cover(path: Path, jpeg_bytes: bytes) -> None:
    suffix = path.suffix.lower()

    if suffix == ".mp3":
        try:
            id3 = ID3(path)
        except ID3NoHeaderError:
            id3 = ID3()
        id3.delall("APIC")
        id3.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=jpeg_bytes))
        id3.save(path)

    elif suffix == ".flac":
        audio = FLAC(path)
        pic = Picture()
        pic.data = jpeg_bytes
        pic.type = 3
        pic.mime = "image/jpeg"
        audio.clear_pictures()
        audio.add_picture(pic)
        audio.save()

    elif suffix in (".ogg", ".opus"):
        audio = OggOpus(path) if suffix == ".opus" else OggVorbis(path)
        pic = Picture()
        pic.data = jpeg_bytes
        pic.type = 3
        pic.mime = "image/jpeg"
        encoded = base64.b64encode(pic.write()).decode("ascii")
        audio["METADATA_BLOCK_PICTURE"] = [encoded]
        audio.save()

    elif suffix == ".m4a":
        audio = MP4(path)
        audio["covr"] = [MP4Cover(jpeg_bytes, imageformat=MP4Cover.FORMAT_JPEG)]
        audio.save()

    # .wav: no standard embedded-art support — text tags still apply.


def apply_tags(path: str | Path, tags: dict[str, Any]) -> None:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(str(path))

    _write_easy_tags(path, tags)

    cover_art_url = tags.get("cover_art_url")
    if cover_art_url:
        try:
            resp = requests.get(cover_art_url, timeout=10)
            resp.raise_for_status()
            _embed_cover(path, resp.content)
        except Exception:
            # Tags already written; a failed cover-art fetch shouldn't fail the whole apply.
            pass
