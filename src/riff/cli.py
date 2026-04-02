"""CLI entry point for riff."""

from __future__ import annotations

from pathlib import Path

import click

from riff import display, download, search


@click.group()
@click.version_option(package_name="riff")
def main() -> None:
    """YouTube Music from your terminal."""


@main.command()
@click.argument("query", nargs=-1, required=True)
@click.option(
    "-t", "--type",
    "result_type",
    type=click.Choice(["song", "album", "artist", "playlist"], case_sensitive=False),
    default="song",
    help="Type of result to search for.",
)
@click.option("-l", "--limit", default=10, show_default=True, help="Maximum number of results.")
def search_cmd(query: tuple[str, ...], result_type: str, limit: int) -> None:
    """Search YouTube Music."""
    query_str = " ".join(query)
    try:
        results = search.search(query_str, result_type=result_type, limit=limit)
    except Exception as e:
        display.print_error(str(e))
        raise SystemExit(1)

    display.display_search_results(results, result_type=result_type)


# Register with the name "search" (can't use it as a Python identifier directly)
search_cmd.name = "search"


@main.command(name="dl")
@click.argument("urls", nargs=-1, required=True)
@click.option(
    "-o", "--output-dir",
    default="~/Music",
    show_default=True,
    help="Output directory for downloaded files.",
)
@click.option(
    "-f", "--format",
    "fmt",
    type=click.Choice(["best", "mp3", "flac", "opus"], case_sensitive=False),
    default="best",
    show_default=True,
    help="Audio format.",
)
def download_cmd(urls: tuple[str, ...], output_dir: str, fmt: str) -> None:
    """Download audio from YouTube Music URLs."""
    progress = display.create_progress()
    tasks: dict[str, int] = {}

    def progress_hook(d: dict) -> None:
        status = d.get("status", "")
        filename = d.get("filename", "downloading")
        filename = Path(filename).stem

        if filename not in tasks:
            tasks[filename] = progress.add_task(filename, total=None)

        task_id = tasks[filename]

        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            if total:
                progress.update(task_id, total=total, completed=downloaded)
        elif status == "finished":
            total = progress.tasks[task_id].total or 0
            progress.update(task_id, completed=total)

    with progress:
        for url in urls:
            try:
                result = download.download_audio(
                    url,
                    output_dir=output_dir,
                    fmt=fmt,
                    progress_callback=progress_hook,
                )
            except Exception as e:
                display.print_error(f"Failed to download {url}: {e}")
                continue

    for url in urls:
        display.print_success(f"Downloaded to {Path(output_dir).expanduser().resolve()}")
        break  # Only print output dir once


@main.command(name="download", hidden=True)
@click.argument("urls", nargs=-1, required=True)
@click.option("-o", "--output-dir", default="~/Music", show_default=True)
@click.option("-f", "--format", "fmt", type=click.Choice(["best", "mp3", "flac", "opus"]), default="best")
@click.pass_context
def download_alias(ctx: click.Context, **kwargs) -> None:  # type: ignore[no-untyped-def]
    """Alias for dl."""
    ctx.invoke(download_cmd, **kwargs)


@main.command()
@click.argument("url_or_id")
def info(url_or_id: str) -> None:
    """Show detailed info for a track."""
    # Extract video ID from URL if needed
    video_id = url_or_id
    if "watch?v=" in video_id:
        video_id = video_id.split("watch?v=")[1].split("&")[0]
    elif "youtu.be/" in video_id:
        video_id = video_id.split("youtu.be/")[1].split("?")[0]

    try:
        track_info = search.get_song_info(video_id)
    except Exception as e:
        display.print_error(str(e))
        raise SystemExit(1)

    display.display_track_info(track_info)
