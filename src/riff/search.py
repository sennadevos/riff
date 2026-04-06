"""ytmusicapi wrapper for searching YouTube Music."""

from __future__ import annotations

from typing import Any

from ytmusicapi import YTMusic


_client: YTMusic | None = None


def _get_client() -> YTMusic:
    global _client
    if _client is None:
        _client = YTMusic()
    return _client


def _format_duration(seconds: int | None) -> str:
    if seconds is None:
        return ""
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


def _extract_song(item: dict[str, Any]) -> dict[str, Any]:
    artists = ", ".join(a["name"] for a in item.get("artists", []) if a.get("name"))
    album = item.get("album", {})
    duration = item.get("duration_seconds") or item.get("duration")
    if isinstance(duration, str):
        # "3:45" -> seconds
        parts = duration.split(":")
        try:
            duration = int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            duration = None
    return {
        "videoId": item.get("videoId"),
        "title": item.get("title", ""),
        "artist": artists,
        "album": album.get("name", "") if isinstance(album, dict) else str(album),
        "duration": _format_duration(duration) if isinstance(duration, int) else str(duration or ""),
    }


def _extract_album(item: dict[str, Any]) -> dict[str, Any]:
    artists = ", ".join(a["name"] for a in item.get("artists", []) if a.get("name"))
    return {
        "browseId": item.get("browseId", ""),
        "title": item.get("title", ""),
        "artist": artists,
        "year": item.get("year", ""),
    }


def _extract_artist(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "browseId": item.get("browseId", ""),
        "name": item.get("artist", ""),
        "subscribers": item.get("subscribers", ""),
    }


def _extract_playlist(item: dict[str, Any]) -> dict[str, Any]:
    author = item.get("author", "")
    if isinstance(author, dict):
        author = author.get("name", "")
    return {
        "playlistId": item.get("playlistId", ""),
        "title": item.get("title", ""),
        "author": author,
        "count": item.get("itemCount", ""),
    }


_FILTERS: dict[str, str] = {
    "song": "songs",
    "album": "albums",
    "artist": "artists",
    "playlist": "community_playlists",
}

_EXTRACTORS = {
    "song": _extract_song,
    "album": _extract_album,
    "artist": _extract_artist,
    "playlist": _extract_playlist,
}


def search_songs(query: str, limit: int = 10) -> list[dict[str, Any]]:
    results = _get_client().search(query, filter="songs", limit=limit)
    return [_extract_song(r) for r in results]


def search_albums(query: str, limit: int = 10) -> list[dict[str, Any]]:
    results = _get_client().search(query, filter="albums", limit=limit)
    return [_extract_album(r) for r in results]


def search_artists(query: str, limit: int = 10) -> list[dict[str, Any]]:
    results = _get_client().search(query, filter="artists", limit=limit)
    return [_extract_artist(r) for r in results]


def search_playlists(query: str, limit: int = 10) -> list[dict[str, Any]]:
    results = _get_client().search(query, filter="community_playlists", limit=limit)
    return [_extract_playlist(r) for r in results]


def search(query: str, result_type: str = "song", limit: int = 10) -> list[dict[str, Any]]:
    yt_filter = _FILTERS.get(result_type, "songs")
    extractor = _EXTRACTORS.get(result_type, _extract_song)
    results = _get_client().search(query, filter=yt_filter, limit=limit)
    return [extractor(r) for r in results][:limit]


def get_song_info(video_id: str) -> dict[str, Any]:
    info = _get_client().get_song(video_id)
    details = info.get("videoDetails", {})
    microformat = info.get("microformat", {}).get("microformatDataRenderer", {})
    thumbnail = ""
    thumbs = details.get("thumbnail", {}).get("thumbnails", [])
    if thumbs:
        thumbnail = thumbs[-1].get("url", "")
    return {
        "videoId": details.get("videoId", video_id),
        "title": details.get("title", ""),
        "artist": details.get("author", ""),
        "duration": _format_duration(int(details["lengthSeconds"])) if details.get("lengthSeconds") else "",
        "views": details.get("viewCount", ""),
        "thumbnail": thumbnail,
        "description": microformat.get("description", ""),
        "url": f"https://music.youtube.com/watch?v={details.get('videoId', video_id)}",
    }
