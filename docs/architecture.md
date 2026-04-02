# Architecture

## Overview

riff is structured as a thin CLI layer on top of two well-established libraries: **ytmusicapi** for interacting with YouTube Music and **yt-dlp** for downloading and converting audio. The CLI is built with **Click** for argument parsing and **Rich** for terminal output.

```
User
  |
  v
cli.py  (Click command group -- entry point)
  |
  +---> search.py   (ytmusicapi -- search & metadata)
  |       |
  +---> download.py (yt-dlp -- audio downloads)
  |       |
  +---> display.py  (Rich -- terminal output formatting)
  |
  +---> config.py   (user configuration)
```

## Modules

### `cli.py` -- Entry point

Click command group that defines the top-level `riff` command and subcommands (`search`, `download`, `info`). Handles argument parsing and delegates to the appropriate module.

### `search.py` -- YouTube Music search

Wraps ytmusicapi to search YouTube Music for songs, albums, artists, and playlists. Returns structured result objects that can be passed to the display module or used by download.

### `download.py` -- Audio downloads

Wraps yt-dlp to download audio in the best available quality. Handles format selection, output path resolution, and metadata embedding. Supports single tracks and full playlists.

### `display.py` -- Terminal output

Uses Rich to render search results as formatted tables, show download progress bars, and display track metadata. Keeps all presentation logic out of the core modules.

### `config.py` -- User configuration

Manages user preferences such as default output directory and preferred audio format. Reads from a config file so users don't have to pass flags every time.

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
