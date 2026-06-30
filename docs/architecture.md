# Architecture

## Overview

riff is structured as a CLI with an interactive TUI, built on top of **ytmusicapi** for YouTube Music interaction and **yt-dlp** for audio downloads. The CLI uses **Click** for argument parsing and **Rich** for terminal output. The TUI uses **urwid** for the interactive interface. An optional **web** frontend (FastAPI) exposes the same search and download over HTTP.

When called without arguments, riff launches the TUI. Subcommands (`search`, `dl`, `info`, `serve`) use the traditional CLI path.

The three frontends (TUI, CLI, web) are thin presentation layers over two shared, framework-agnostic cores: `search.py` and `download.py`. Adding a frontend means wiring those two modules to a new I/O surface — no download or search logic is duplicated.

```
User
  |
  +-- terminal --> cli.py (Click command group -- entry point)
  |                  |
  |                  +-- no args ----> tui/app.py  (urwid -- interactive TUI)
  |                  +-- `serve` ----> web/app.py  (FastAPI -- HTTP frontend)
  |                  +-- else -------> display.py   (Rich -- CLI output formatting)
  |
  +-- browser ----> web/app.py
                       |
       all of the above call into:
                       |
                  search.py   (ytmusicapi -- search & metadata)
                  download.py (yt-dlp -- audio downloads, progress callbacks)
```

## Modules

### `cli.py` -- Entry point

Click command group with `invoke_without_command=True`. When no subcommand is given, launches the TUI. Subcommands: `search`, `dl` (with hidden `download` alias), `info`, `serve`. `serve` lazily imports the web dependencies so they stay optional for terminal-only users.

### `tui/app.py` -- Interactive TUI

urwid-based TUI with vim-style navigation. Provides search, result browsing, track info with album art (kitty graphics protocol), and downloading with progress. All blocking I/O (search, download, info fetch) runs in background threads with thread-safe UI updates via urwid's pipe mechanism.

### `search.py` -- YouTube Music search

Wraps ytmusicapi to search YouTube Music for songs, albums, artists, and playlists. Returns structured result dicts. Uses a lazy-initialized singleton client.

### `download.py` -- Audio downloads

Wraps yt-dlp to download audio in the best available quality. Handles format selection, output path resolution, and metadata embedding (including album art via mutagen). Supports single tracks and full playlists.

### `display.py` -- Terminal output

Uses Rich to render search results as formatted tables, show download progress bars, and display track metadata. Supports album art display via `kitten icat` in kitty terminals. Used by CLI subcommands only (TUI has its own rendering).

### `web/` -- Web frontend (optional)

A single-page FastAPI app served by `riff serve`. `web/app.py` reuses `search.py` and `download.py` unchanged: `GET /api/search` returns results as JSON (including a lazily-loaded cover thumbnail), and `POST /api/download` runs the download in a worker thread, relaying yt-dlp's progress callbacks to the browser as Server-Sent Events. `web/static/index.html` is a dependency-free page (no build step). The download directory is resolved from `$RIFF_MUSIC_DIR` (or `riff serve --music-dir`), defaulting to `~/Music`. Dependencies live behind the `web` extra (`pip install '.[web]'`).

## Design decisions

### Why ytmusicapi

- No API key required -- works out of the box without Google Cloud setup
- Purpose-built for YouTube Music, unlike the general YouTube Data API
- Returns music-specific metadata (album, artist, duration) directly

### Why yt-dlp

- Battle-tested with broad format and site support
- Best-in-class audio extraction and format conversion
- Active maintenance and rapid fixes when YouTube changes
- Built-in support for playlist handling and metadata embedding

### Why urwid (not Textual)

- Uses terminal's native colors -- no CSS theming system to fight
- Direct control over widgets and key handling
- Works well in toolbox/container environments
- Kitty graphics protocol integration via direct escape sequences (works in containers where `kitten` binary isn't available)

### Kitty album art

Album art in the TUI uses the kitty graphics protocol directly (base64-encoded PNG escape sequences written to `/dev/tty`). This avoids needing the `kitten` binary and works inside toolbox containers. JPEGs from YouTube are converted to PNG via Pillow since the protocol only supports PNG format (`f=100`).

### Why FastAPI + Server-Sent Events

- The web frontend is an *optional* extra, so it must not weigh down the core install — FastAPI/Uvicorn live behind the `web` extra and are imported lazily.
- A download is long-running with incremental progress, which maps naturally onto Server-Sent Events: a one-way stream from server to browser, no WebSocket handshake or client library needed. The browser reads the stream over the same `fetch` it used to start the download.
- yt-dlp's blocking work runs in a worker thread while the event loop relays its progress callbacks, keeping the server responsive without rewriting the download path.
- The page is intentionally a single static HTML file with no build step, mirroring the "no toolchain to fight" spirit of the urwid TUI choice.
