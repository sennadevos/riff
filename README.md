# riff

YouTube Music from your terminal.

**riff** combines [ytmusicapi](https://github.com/sigma67/ytmusicapi) for search and metadata with [yt-dlp](https://github.com/yt-dlp/yt-dlp) for high-quality audio downloads, all wrapped in a clean CLI.

## Features

- Search songs, albums, artists, and playlists on YouTube Music
- Download highest quality audio (opus, m4a, mp3, and more)
- Rich terminal output with formatted tables and progress bars
- Full playlist support -- download entire playlists in one command
- Automatic metadata embedding (title, artist, album, cover art)

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
```

### Download

```sh
# Download a track (best available quality)
riff download <url>

# Download as mp3
riff download <url> --format mp3

# Download an entire playlist
riff download <playlist-url>
```

### Info

```sh
# Show track metadata
riff info <url>
```

## Dependencies

| Package | Purpose |
|---|---|
| [ytmusicapi](https://github.com/sigma67/ytmusicapi) | YouTube Music search and metadata |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Audio downloading and format conversion |
| [click](https://click.palletsprojects.com/) | CLI framework |
| [rich](https://github.com/Textualize/rich) | Terminal formatting and progress bars |

## License

[MIT](LICENSE)
