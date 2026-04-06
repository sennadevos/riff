# riff

YouTube Music from your terminal.

**riff** combines [ytmusicapi](https://github.com/sigma67/ytmusicapi) for search and metadata with [yt-dlp](https://github.com/yt-dlp/yt-dlp) for high-quality audio downloads, wrapped in both a CLI and an interactive TUI.

## Features

- Interactive TUI with vim-style navigation (runs when called without arguments)
- Search songs, albums, artists, and playlists on YouTube Music
- Download highest quality audio (opus, flac, mp3)
- Rich terminal output with formatted tables and progress bars
- Full playlist support -- download entire playlists in one command
- Automatic metadata embedding (title, artist, album, cover art)
- Album art display in kitty terminal (TUI and CLI `info` command)

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

### Search

```sh
# Search for a song
riff search "vini vici adhana"

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

## License

[MIT](LICENSE)
