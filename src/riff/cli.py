"""CLI entry point for riff."""

from __future__ import annotations

from pathlib import Path

import click

from riff import display, download, search


@click.group(invoke_without_command=True)
@click.version_option(package_name="riff")
@click.pass_context
def main(ctx: click.Context) -> None:
    """YouTube Music from your terminal."""
    if ctx.invoked_subcommand is None:
        from riff.tui.app import RiffApp

        RiffApp().run()


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
@click.option("--url", is_flag=True, help="Output YouTube Music URLs only, one per line.")
@click.option("--id", "id_only", is_flag=True, help="Output video/browse/playlist IDs only, one per line.")
def search_cmd(query: tuple[str, ...], result_type: str, limit: int, url: bool, id_only: bool) -> None:
    """Search YouTube Music."""
    query_str = " ".join(query)
    try:
        results = search.search(query_str, result_type=result_type, limit=limit)
    except Exception as e:
        display.print_error(str(e))
        raise SystemExit(1)

    if url:
        for r in results:
            vid = r.get("videoId") or r.get("playlistId") or r.get("browseId", "")
            if vid:
                if r.get("videoId"):
                    click.echo(f"https://music.youtube.com/watch?v={vid}")
                elif r.get("playlistId"):
                    click.echo(f"https://music.youtube.com/playlist?list={vid}")
                else:
                    click.echo(f"https://music.youtube.com/browse/{vid}")
    elif id_only:
        for r in results:
            vid = r.get("videoId") or r.get("playlistId") or r.get("browseId", "")
            if vid:
                click.echo(vid)
    else:
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

    failed = []
    with progress:
        for url in urls:
            try:
                download.download_audio(
                    url,
                    output_dir=output_dir,
                    fmt=fmt,
                    progress_callback=progress_hook,
                )
            except Exception as e:
                failed.append(url)
                display.print_error(f"Failed to download {url}: {e}")
                continue

    succeeded = len(urls) - len(failed)
    if succeeded:
        display.print_success(f"Downloaded {succeeded} track(s) to {Path(output_dir).expanduser().resolve()}")


@main.command(name="download", hidden=True)
@click.argument("urls", nargs=-1, required=True)
@click.option("-o", "--output-dir", default="~/Music", show_default=True)
@click.option("-f", "--format", "fmt", type=click.Choice(["best", "mp3", "flac", "opus"]), default="best")
@click.pass_context
def download_alias(ctx: click.Context, **kwargs: str | tuple[str, ...]) -> None:
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
