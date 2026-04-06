"""Rich formatting for terminal output."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Any
from urllib.request import urlretrieve

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table
from rich.text import Text


console = Console()

_ACCENT = "cyan"
_SUCCESS = "green"
_ERROR = "red bold"


def _in_kitty() -> bool:
    return os.environ.get("TERM", "") == "xterm-kitty" or "kitty" in os.environ.get("TERM_PROGRAM", "").lower()


def _has_kitten() -> bool:
    return shutil.which("kitten") is not None


def show_image(url: str, width: int = 40) -> bool:
    """Download and display an image using kitten icat. Returns True if shown."""
    if not _in_kitty() or not _has_kitten():
        return False
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            urlretrieve(url, tmp.name)
            subprocess.run(
                ["kitten", "icat", "--align", "left", f"--place={width}x{width}@0x0", tmp.name],
                check=True,
            )
            os.unlink(tmp.name)
        return True
    except Exception:
        return False


def show_image_simple(url: str) -> bool:
    """Download and display an image using kitten icat, simple mode."""
    if not _in_kitty() or not _has_kitten():
        return False
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            urlretrieve(url, tmp.name)
            subprocess.run(["kitten", "icat", tmp.name], check=True)
            os.unlink(tmp.name)
        return True
    except Exception:
        return False


def display_search_results(results: list[dict[str, Any]], result_type: str = "song") -> None:
    if not results:
        console.print(f"[dim]No {result_type} results found.[/dim]")
        return

    table = Table(show_header=True, header_style=f"bold {_ACCENT}", padding=(0, 1))

    if result_type == "song":
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="bold")
        table.add_column("Artist")
        table.add_column("Album", style="dim")
        table.add_column("Duration", justify="right")
        table.add_column("ID", style="dim")
        for i, r in enumerate(results, 1):
            table.add_row(str(i), r.get("title", ""), r.get("artist", ""), r.get("album", ""), r.get("duration", ""), r.get("videoId", ""))
    elif result_type == "album":
        table.add_column("#", style="dim", width=4)
        table.add_column("Album", style="bold")
        table.add_column("Artist")
        table.add_column("Year", justify="right")
        table.add_column("ID", style="dim")
        for i, r in enumerate(results, 1):
            table.add_row(str(i), r.get("title", ""), r.get("artist", ""), str(r.get("year", "")), r.get("browseId", ""))
    elif result_type == "artist":
        table.add_column("#", style="dim", width=4)
        table.add_column("Artist", style="bold")
        table.add_column("Subscribers", justify="right")
        table.add_column("ID", style="dim")
        for i, r in enumerate(results, 1):
            table.add_row(str(i), r.get("name", ""), r.get("subscribers", ""), r.get("browseId", ""))
    elif result_type == "playlist":
        table.add_column("#", style="dim", width=4)
        table.add_column("Playlist", style="bold")
        table.add_column("Author")
        table.add_column("Tracks", justify="right")
        table.add_column("ID", style="dim")
        for i, r in enumerate(results, 1):
            table.add_row(str(i), r.get("title", ""), r.get("author", ""), str(r.get("count", "")), r.get("playlistId", ""))

    console.print(table)


def create_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=40),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    )


def display_track_info(info: dict[str, Any]) -> None:
    # Show album art via Kitty if available
    if info.get("thumbnail"):
        show_image_simple(info["thumbnail"])
        console.print()

    lines: list[str] = []
    if info.get("title"):
        lines.append(f"[bold]{info['title']}[/bold]")
    if info.get("artist"):
        lines.append(f"[{_ACCENT}]Artist:[/{_ACCENT}]  {info['artist']}")
    if info.get("duration"):
        lines.append(f"[{_ACCENT}]Duration:[/{_ACCENT}] {info['duration']}")
    if info.get("views"):
        lines.append(f"[{_ACCENT}]Views:[/{_ACCENT}]    {int(info['views']):,}" if info["views"].isdigit() else f"[{_ACCENT}]Views:[/{_ACCENT}]    {info['views']}")
    if info.get("url"):
        lines.append(f"[{_ACCENT}]URL:[/{_ACCENT}]      {info['url']}")
    if info.get("description"):
        desc = info["description"][:200]
        if len(info["description"]) > 200:
            desc += "..."
        lines.append(f"\n[dim]{desc}[/dim]")

    panel = Panel("\n".join(lines), title="Track Info", border_style=_ACCENT, padding=(1, 2))
    console.print(panel)


def print_error(message: str) -> None:
    console.print(Text(f"Error: {message}", style=_ERROR))


def print_success(message: str) -> None:
    console.print(Text(message, style=_SUCCESS))
