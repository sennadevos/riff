# riff

YouTube Music from your terminal.

**riff** combines [ytmusicapi](https://github.com/sigma67/ytmusicapi) for search and metadata with [yt-dlp](https://github.com/yt-dlp/yt-dlp) for high-quality audio downloads, wrapped in both a CLI and an interactive TUI.

## Features

- Interactive TUI with vim-style navigation (runs when called without arguments)
- Search songs, videos, albums, artists, and playlists on YouTube Music
  (video search surfaces tracks not listed as songs)
- Download highest quality audio (opus, flac, mp3)
- Rich terminal output with formatted tables and progress bars
- Full playlist support -- download entire playlists in one command
- Automatic metadata embedding (title, artist, album, cover art)
- Album art display in kitty terminal (TUI and CLI `info` command)
- Optional one-page web UI (`riff serve`) for searching and downloading from a browser

## Installation

Requires Python 3.10+.

```
pip install .
```

Or with [pipx](https://pipx.pypa.io/) for isolated installs:

```
pipx install .
```

## Usage

### TUI

Launch the interactive browser by running `riff` with no arguments:

```sh
riff
```

**Keybindings:**

| Key | Action |
|-----|--------|
| `/` | Focus search input |
| `j` / `k` | Navigate up/down |
| `g` / `G` | Jump to top/bottom |
| `l` / `Enter` | Open track info |
| `h` / `q` | Go back / close |
| `d` | Download selected track |
| `Tab` | Cycle result type |
| `1`-`4` | Switch to songs/albums/artists/playlists |
| `Ctrl+C` (x2) | Quit |

### Web

riff ships an optional one-page web frontend for searching and downloading from a
browser — handy for adding music to a watched folder without opening a terminal.
Install the web extra and run `riff serve`:

```sh
pip install '.[web]'
riff serve                                   # http://0.0.0.0:8080, downloads to ~/Music
riff serve --port 9000 --music-dir /srv/music
```

Then open the printed URL, search, and click **Download** — covers load lazily, progress
streams live in the page, and files land in `--music-dir` (override with `$RIFF_MUSIC_DIR`).

Two source toggles: **YouTube Music** (songs/videos/playlists, as above) and
**SoundCloud** (track search only, via yt-dlp's `scsearch` — no API key needed).
Downloading a SoundCloud URL works the same as any other, since `download_audio`
just hands the URL to yt-dlp.

A **Library** tab lists what's already in your music directory, recursively (title/artist
from tags, file size) with a **Delete** button — simple view + delete, nothing more.

The Library tab also has a **Scan** button that identifies every track via Shazam's
audio recognition (through [shazamio](https://github.com/shazamio/ShazamIO) — no API key
needed). Scanning is **manually triggered only** and never writes anything by itself: it
shows each identified title/artist/album/year next to the file's current tags, and only
applies a fix when you click that result's **Apply** button — one track at a time, so
your library is never touched without an explicit decision per file.

| Endpoint | Description |
|---|---|
| `GET /api/search?q=&type=song\|video\|playlist&source=ytmusic\|soundcloud&limit=` | Search results as JSON |
| `POST /api/download` `{url, format, playlist}` | Download, streaming progress as Server-Sent Events |
| `GET /api/library` | List files in the music directory (recursive) |
| `DELETE /api/library/{path}` | Delete a file from the music directory |
| `POST /api/scan` | Identify every library track via Shazam, streaming results as Server-Sent Events |
| `POST /api/scan/apply` `{filename, title, artist, album, year, genre, cover_art_url}` | Write tags + embed cover art for one track |
| `GET /healthz` | Liveness + resolved download directory |

A `Containerfile` is included to run the web frontend in a container:

```sh
podman build -t riff-web .
podman run -p 8080:8080 -v ~/Music:/music:z -e RIFF_MUSIC_DIR=/music riff-web
```

> The web UI has no authentication and triggers downloads — keep it on a trusted
> network, not the public internet.

### Search

```sh
# Search for a song
riff search "vini vici adhana"

# Search videos (finds tracks not listed as songs)
riff search "vini vici adhana" --type video

# Search for artists
riff search "vini vici" --type artist

# Search for albums
riff search "future primitives" --type album

# Search for playlists
riff search "psytrance mix" --type playlist

# Output URLs only
riff search "vini vici" --url

# Output IDs only
riff search "vini vici" --id
```

### Download

```sh
# Download a track (best available quality)
riff dl <url>

# Download as mp3
riff dl <url> --format mp3

# Download an entire playlist
riff dl <playlist-url>
```

### Info

```sh
# Show track metadata (with album art in kitty)
riff info <url>
```

## Desktop entry

A `.desktop` file is included for launching riff in a kitty window:

```sh
cp riff.desktop ~/.local/share/applications/
```

## Dependencies

| Package | Purpose |
|---|---|
| [ytmusicapi](https://github.com/sigma67/ytmusicapi) | YouTube Music search and metadata |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Audio downloading and format conversion |
| [click](https://click.palletsprojects.com/) | CLI framework |
| [rich](https://github.com/Textualize/rich) | Terminal formatting and progress bars |
| [urwid](https://urwid.org/) | TUI framework |
| [Pillow](https://python-pillow.org/) | Image conversion for kitty graphics protocol |
| [mutagen](https://mutagen.readthedocs.io/) | Audio metadata embedding |

Installing the `web` extra (`pip install '.[web]'`) additionally pulls in:

| Package | Purpose |
|---|---|
| [FastAPI](https://fastapi.tiangolo.com/) | Web framework for the `riff serve` frontend |
| [Uvicorn](https://www.uvicorn.org/) | ASGI server that runs the web app |

## License

[MIT](LICENSE)
