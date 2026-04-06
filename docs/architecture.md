# Architecture

## Overview

riff is structured as a CLI with an interactive TUI, built on top of **ytmusicapi** for YouTube Music interaction and **yt-dlp** for audio downloads. The CLI uses **Click** for argument parsing and **Rich** for terminal output. The TUI uses **urwid** for the interactive interface.

When called without arguments, riff launches the TUI. Subcommands (`search`, `dl`, `info`) use the traditional CLI path.

```
User
  |
  v
cli.py  (Click command group -- entry point)
  |
  +---> tui/app.py  (urwid -- interactive TUI, launched with no args)
  |       |
  +---> search.py   (ytmusicapi -- search & metadata)
  |       |
  +---> download.py (yt-dlp -- audio downloads)
  |       |
  +---> display.py  (Rich -- CLI terminal output formatting)
  |
  +---> config.py   (user configuration)
```

## Modules

### `cli.py` -- Entry point

Click command group with `invoke_without_command=True`. When no subcommand is given, launches the TUI. Subcommands: `search`, `dl` (with hidden `download` alias), `info`.

### `tui/app.py` -- Interactive TUI

urwid-based TUI with vim-style navigation. Provides search, result browsing, track info with album art (kitty graphics protocol), and downloading with progress. All blocking I/O (search, download, info fetch) runs in background threads with thread-safe UI updates via urwid's pipe mechanism.

### `search.py` -- YouTube Music search

Wraps ytmusicapi to search YouTube Music for songs, albums, artists, and playlists. Returns structured result dicts. Uses a lazy-initialized singleton client.

### `download.py` -- Audio downloads

Wraps yt-dlp to download audio in the best available quality. Handles format selection, output path resolution, and metadata embedding (including album art via mutagen). Supports single tracks and full playlists.

### `display.py` -- Terminal output

Uses Rich to render search results as formatted tables, show download progress bars, and display track metadata. Supports album art display via `kitten icat` in kitty terminals. Used by CLI subcommands only (TUI has its own rendering).

### `config.py` -- User configuration

Manages user preferences such as default output directory and preferred audio format.

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
