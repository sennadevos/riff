"""TUI application for riff using urwid."""

from __future__ import annotations

import base64
import os
import queue
import tempfile
import threading
from typing import Any
from urllib.request import urlretrieve

import urwid

from riff import download, search

RESULT_TYPES = ["song", "album", "artist", "playlist"]

PALETTE = [
    ("header", "white,bold", ""),
    ("accent", "light cyan", ""),
    ("dim", "dark gray", ""),
    ("cursor", "standout", ""),
    ("col_header", "light cyan,bold", ""),
    ("status", "dark gray", ""),
    ("info_key", "light cyan", ""),
    ("info_title", "white,bold", ""),
    ("error", "light red", ""),
    ("success", "light green", ""),
    ("progress_done", "light cyan", "dark cyan"),
    ("progress_left", "", "dark gray"),
    ("edit", "white", ""),
]

_WORD_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")


def _in_kitty() -> bool:
    return os.environ.get("TERM", "") == "xterm-kitty" or "kitty" in os.environ.get("TERM_PROGRAM", "").lower()


def _download_thumbnail(url: str) -> str | None:
    """Download thumbnail to a temp file. Returns path or None."""
    if not url:
        return None
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        urlretrieve(url, tmp.name)
        tmp.close()
        return tmp.name
    except Exception:
        return None


def _kitty_display_image(image_path: str, cols: int = 0, rows: int = 0) -> None:
    """Display image using kitty graphics protocol escape sequences.

    Converts to PNG first since kitty's f=100 only accepts PNG format.
    cols/rows: if set, tells kitty to scale the image to fit this many cells.
    """
    import io
    from PIL import Image as PILImage

    img = PILImage.open(image_path)
    # shrink large images to keep payload small
    if img.width > 400 or img.height > 400:
        img.thumbnail((400, 400))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()

    encoded = base64.b64encode(data).decode("ascii")
    chunk_size = 4096
    chunks = [encoded[i:i + chunk_size] for i in range(0, len(encoded), chunk_size)]

    # build first chunk header with optional cell scaling
    extra = ""
    if cols:
        extra += f",c={cols}"
    if rows:
        extra += f",r={rows}"

    tty_fd = os.open("/dev/tty", os.O_WRONLY)
    for i, chunk in enumerate(chunks):
        m = 1 if i < len(chunks) - 1 else 0
        if i == 0:
            header = f"\x1b_Ga=T,f=100,t=d{extra},m={m};"
        else:
            header = f"\x1b_Gm={m};"
        os.write(tty_fd, (header + chunk + "\x1b\\").encode())
    os.close(tty_fd)


def _kitty_clear_images() -> None:
    """Clear all kitty image placements."""
    try:
        tty_fd = os.open("/dev/tty", os.O_WRONLY)
        os.write(tty_fd, b"\x1b_Ga=d;\x1b\\")
        os.close(tty_fd)
    except Exception:
        pass


class SearchEdit(urwid.Edit):
    """Search input with Enter submit and word-level editing."""

    signals = ["submit"]

    def __init__(self) -> None:
        super().__init__(("accent", "/ "), "")

    def keypress(self, size, key):
        if key == "enter":
            urwid.emit_signal(self, "submit", self.edit_text.strip())
            return None
        if key == "ctrl w":
            self._delete_word_back()
            return None
        if key == "meta backspace":
            self._delete_word_back()
            return None
        if key in ("ctrl left", "meta b"):
            self._move_word_left()
            return None
        if key in ("ctrl right", "meta f"):
            self._move_word_right()
            return None
        if key == "ctrl u":
            self.set_edit_text("")
            self.set_edit_pos(0)
            return None
        return super().keypress(size, key)

    def _delete_word_back(self) -> None:
        text = self.edit_text
        pos = self.edit_pos
        if pos == 0:
            return
        i = pos - 1
        while i > 0 and text[i] not in _WORD_CHARS:
            i -= 1
        while i > 0 and text[i - 1] in _WORD_CHARS:
            i -= 1
        self.set_edit_text(text[:i] + text[pos:])
        self.set_edit_pos(i)

    def _move_word_left(self) -> None:
        text = self.edit_text
        pos = self.edit_pos
        if pos == 0:
            return
        i = pos - 1
        while i > 0 and text[i] not in _WORD_CHARS:
            i -= 1
        while i > 0 and text[i - 1] in _WORD_CHARS:
            i -= 1
        self.set_edit_pos(i)

    def _move_word_right(self) -> None:
        text = self.edit_text
        pos = self.edit_pos
        length = len(text)
        if pos >= length:
            return
        i = pos
        while i < length and text[i] not in _WORD_CHARS:
            i += 1
        while i < length and text[i] in _WORD_CHARS:
            i += 1
        self.set_edit_pos(i)


class SelectableRow(urwid.WidgetWrap):
    """A row that is selectable and passes keys through."""

    def __init__(self, widget):
        super().__init__(widget)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class InfoBody(urwid.WidgetWrap):
    """Selectable info content that handles esc/q/d keys."""

    signals = ["close", "download"]

    def __init__(self, content_widget):
        super().__init__(content_widget)

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key in ("esc", "q", "escape", "h"):
            urwid.emit_signal(self, "close")
            return None
        if key == "d":
            urwid.emit_signal(self, "download")
            return None
        return self._w.keypress(size, key)


class ResultList(urwid.ListBox):
    """Navigable results list with vim keys."""

    signals = ["select", "download", "info"]

    def keypress(self, size, key):
        if key in ("j", "down"):
            return super().keypress(size, "down")
        if key in ("k", "up"):
            return super().keypress(size, "up")
        if key == "g":
            if self.body:
                self.set_focus(0)
            return None
        if key == "G":
            if self.body:
                self.set_focus(len(self.body) - 1)
            return None
        if key in ("enter", "l"):
            urwid.emit_signal(self, "select")
            return None
        if key == "d":
            urwid.emit_signal(self, "download")
            return None
        if key == "i":
            urwid.emit_signal(self, "info")
            return None
        return super().keypress(size, key)


class RiffApp:
    """Interactive YouTube Music browser."""

    def __init__(self) -> None:
        self._result_type = "song"
        self._current_results: list[dict[str, Any]] = []
        self._last_query = ""
        self._ctrl_c_pending = False

        self._callback_queue: queue.Queue = queue.Queue()
        self._pipe_fd: int | None = None

        # search input
        self._search = SearchEdit()
        urwid.connect_signal(self._search, "submit", self._on_search)

        # type selector
        self._type_label = urwid.Text(self._build_type_label())

        # results — only data rows go in the walker (no header/divider)
        self._result_walker = urwid.SimpleFocusListWalker([])
        self._result_list = ResultList(self._result_walker)
        urwid.connect_signal(self._result_list, "select", self._on_select)
        urwid.connect_signal(self._result_list, "download", self._on_download)
        urwid.connect_signal(self._result_list, "info", self._on_info)

        # column header (sits above the list, not inside it)
        self._col_header = urwid.Text("")
        self._col_header_row = urwid.Pile([self._col_header, urwid.Divider("─")])

        # status bar
        self._status = urwid.Text(("status", "/ search  j/k nav  l info  d download  tab type  q quit"))

        # progress bar
        self._progress_text = urwid.Text("")
        self._progress_bar = urwid.ProgressBar("progress_left", "progress_done", 0, 100)
        self._progress_row = urwid.Columns([
            ("pack", self._progress_text),
            self._progress_bar,
        ])

        # body: column header + results list stacked
        self._results_body = urwid.Pile([
            ("pack", self._col_header_row),
            self._result_list,
        ])

        # empty state
        self._empty_filler = urwid.Filler(
            urwid.Text(("dim", "search for music to get started"), align="center"),
            valign="middle",
        )

        # main frame
        self._frame = urwid.Frame(
            body=self._empty_filler,
            header=urwid.Pile([
                urwid.AttrMap(self._search, "edit"),
                self._type_label,
                urwid.Divider("─"),
            ]),
            footer=urwid.Pile([
                urwid.Divider("─"),
                self._status,
            ]),
        )

        self._overlay: urwid.Overlay | None = None
        self._overlay_info: dict[str, Any] | None = None
        self._thumb_path: str | None = None
        self._loop: urwid.MainLoop | None = None

    def run(self) -> None:
        self._loop = urwid.MainLoop(
            self._frame,
            palette=PALETTE,
            unhandled_input=self._unhandled_input,
            handle_mouse=False,
        )
        self._pipe_fd = self._loop.watch_pipe(self._process_callbacks)
        self._loop.run()

    def _process_callbacks(self, _data: bytes) -> bool:
        while not self._callback_queue.empty():
            try:
                fn = self._callback_queue.get_nowait()
                fn()
            except queue.Empty:
                break
        return True

    def _invoke(self, fn) -> None:
        self._callback_queue.put(fn)
        if self._pipe_fd is not None:
            try:
                os.write(self._pipe_fd, b"1")
            except OSError:
                pass

    # --- Input handling ---

    def _unhandled_input(self, key: str) -> bool:
        if key == "q":
            if self._overlay:
                self._close_overlay()
                return True
            raise urwid.ExitMainLoop()
        if key == "ctrl c":
            if self._ctrl_c_pending:
                raise urwid.ExitMainLoop()
            self._ctrl_c_pending = True
            self._status.set_text(("dim", "press ctrl+c again to quit"))
            if self._loop:
                self._loop.set_alarm_in(1.5, lambda *_: self._reset_ctrl_c())
            return True
        if key == "/":
            self._frame.set_focus("header")
            return True
        if key == "tab":
            self._cycle_type()
            return True
        if key in ("esc", "escape", "h"):
            if self._overlay:
                self._close_overlay()
                return True
            if key != "h":  # only esc goes back to results from search
                self._frame.set_focus("body")
            return True
        if key == "d" and self._overlay:
            self._on_download()
            return True
        for i, t in enumerate(RESULT_TYPES, 1):
            if key == str(i):
                self._set_type(t)
                return True
        return False

    def _reset_ctrl_c(self) -> None:
        self._ctrl_c_pending = False
        self._status.set_text(("status", "/ search  j/k nav  l info  d download  tab type  q quit"))

    # --- Type selector ---

    def _build_type_label(self) -> list:
        parts: list = []
        for i, t in enumerate(RESULT_TYPES, 1):
            if parts:
                parts.append("  ")
            if t == self._result_type:
                parts.append(("accent", t))
            else:
                parts.append(("dim", f"{i}:{t}"))
        return parts

    def _refresh_type_label(self) -> None:
        self._type_label.set_text(self._build_type_label())

    def _set_type(self, result_type: str) -> None:
        if result_type == self._result_type:
            return
        self._result_type = result_type
        self._refresh_type_label()
        if self._last_query:
            self._run_search(self._last_query, self._result_type)

    def _cycle_type(self) -> None:
        idx = RESULT_TYPES.index(self._result_type)
        self._set_type(RESULT_TYPES[(idx + 1) % len(RESULT_TYPES)])

    # --- Search ---

    def _on_search(self, query: str) -> None:
        if not query:
            return
        self._last_query = query
        self._run_search(query, self._result_type)

    def _run_search(self, query: str, result_type: str) -> None:
        self._frame.body = urwid.Filler(
            urwid.Text(("dim", "searching..."), align="center"), valign="middle",
        )

        def _do_search():
            try:
                results = search.search(query, result_type=result_type, limit=20)
                self._invoke(lambda: self._populate_results(results, result_type))
            except Exception as e:
                self._invoke(lambda: self._show_error(f"search failed: {e}"))

        threading.Thread(target=_do_search, daemon=True).start()

    def _show_error(self, msg: str) -> None:
        self._status.set_text(("error", msg))
        self._frame.body = urwid.Filler(
            urwid.Text(("dim", "search failed"), align="center"), valign="middle",
        )

    def _populate_results(self, results: list[dict[str, Any]], result_type: str) -> None:
        self._current_results = results

        if not results:
            self._frame.body = urwid.Filler(
                urwid.Text(("dim", "no results found"), align="center"), valign="middle",
            )
            return

        # update column header
        cols = self._columns_for_type(result_type)
        header_parts = []
        for label, _key, w in cols:
            header_parts.append((w, urwid.Text(("col_header", label))))
        self._col_header_row.contents = [
            (urwid.Columns(header_parts, dividechars=1), ("pack", None)),
            (urwid.Divider("─"), ("pack", None)),
        ]

        # build data rows — all selectable
        rows: list[urwid.Widget] = []
        for i, r in enumerate(results, 1):
            row_cols = self._build_row(i, r, result_type, cols)
            rows.append(urwid.AttrMap(SelectableRow(row_cols), None, focus_map="cursor"))

        self._result_walker[:] = rows
        if rows:
            self._result_list.set_focus(0)
        self._results_body.focus_position = 1  # focus the ResultList, not the header
        self._frame.body = self._results_body
        self._frame.set_focus("body")

    def _columns_for_type(self, result_type: str) -> list[tuple[str, str, int]]:
        if result_type == "song":
            return [("#", "#", 4), ("Title", "title", 30), ("Artist", "artist", 20), ("Album", "album", 20), ("Duration", "duration", 8)]
        elif result_type == "album":
            return [("#", "#", 4), ("Album", "title", 30), ("Artist", "artist", 25), ("Year", "year", 6)]
        elif result_type == "artist":
            return [("#", "#", 4), ("Artist", "name", 35), ("Subscribers", "subscribers", 15)]
        else:
            return [("#", "#", 4), ("Playlist", "title", 30), ("Author", "author", 25), ("Tracks", "count", 8)]

    def _build_row(self, idx: int, r: dict, result_type: str, cols: list) -> urwid.Columns:
        values: dict[str, str] = {"#": str(idx)}
        if result_type == "song":
            values.update(title=r.get("title", ""), artist=r.get("artist", ""), album=r.get("album", ""), duration=r.get("duration", ""))
        elif result_type == "album":
            values.update(title=r.get("title", ""), artist=r.get("artist", ""), year=str(r.get("year", "")))
        elif result_type == "artist":
            values.update(name=r.get("name", ""), subscribers=r.get("subscribers", ""))
        else:
            values.update(title=r.get("title", ""), author=r.get("author", ""), count=str(r.get("count", "")))

        col_widgets = []
        for _label, key, w in cols:
            text = values.get(key, "")
            if key == "#":
                col_widgets.append((w, urwid.Text(("dim", text))))
            else:
                col_widgets.append((w, urwid.Text(text)))
        return urwid.Columns(col_widgets, dividechars=1)

    # --- Info ---

    def _on_select(self) -> None:
        self._show_info()

    def _on_info(self) -> None:
        self._show_info()

    def _show_info(self) -> None:
        result = self._get_selected_result()
        if not result:
            return
        vid = result.get("videoId")
        if not vid:
            self._status.set_text(("dim", "info only available for songs"))
            return
        self._status.set_text(("dim", "loading..."))

        def _do_info():
            try:
                info = search.get_song_info(vid)
                thumb_path = _download_thumbnail(info.get("thumbnail", ""))
                self._invoke(lambda: self._show_info_overlay(info, thumb_path))
            except Exception as e:
                self._invoke(lambda: self._status.set_text(("error", f"failed: {e}")))

        threading.Thread(target=_do_info, daemon=True).start()

    def _show_info_overlay(self, info: dict[str, Any], thumb_path: str | None = None) -> None:
        self._overlay_info = info
        self._thumb_path = thumb_path
        self._status.set_text(("status", "h/q close  d download"))

        # calculate image row height to reserve space above text
        try:
            term_rows = os.get_terminal_size().lines
        except Exception:
            term_rows = 24
        self._img_rows = max(6, term_rows // 4) if thumb_path and _in_kitty() else 0

        lines: list[urwid.Widget] = []
        # reserve blank lines for cover art
        for _ in range(self._img_rows):
            lines.append(urwid.Text(""))
        if self._img_rows:
            lines.append(urwid.Divider("─"))
        lines.append(urwid.Text(("info_title", info.get("title", ""))))
        lines.append(urwid.Divider())
        if info.get("artist"):
            lines.append(urwid.Text([("info_key", "artist    "), info["artist"]]))
        if info.get("duration"):
            lines.append(urwid.Text([("info_key", "duration  "), info["duration"]]))
        if info.get("views"):
            views = info["views"]
            if isinstance(views, str) and views.isdigit():
                views = f"{int(views):,}"
            lines.append(urwid.Text([("info_key", "views     "), str(views)]))
        if info.get("url"):
            lines.append(urwid.Text([("info_key", "url       "), info["url"]]))
        if info.get("description"):
            desc = info["description"][:300]
            if len(info["description"]) > 300:
                desc += "..."
            lines.append(urwid.Divider())
            lines.append(urwid.Text(("dim", desc)))

        pile = urwid.Pile(lines)
        filler = urwid.Filler(pile, valign="top")
        info_body = InfoBody(filler)
        urwid.connect_signal(info_body, "close", self._close_overlay)
        urwid.connect_signal(info_body, "download", lambda: self._on_download())
        box = urwid.LineBox(info_body, title="info", title_attr="accent")

        self._overlay = urwid.Overlay(
            box, self._frame,
            align="center", width=("relative", 70),
            valign="middle", height=("relative", 60),
        )
        self._loop.widget = self._overlay

        # show cover art via kitty graphics protocol
        # use an alarm so it fires after urwid finishes all pending redraws
        if thumb_path and _in_kitty():
            self._loop.set_alarm_in(0.05, lambda *_: self._display_cover_art())

    def _display_cover_art(self) -> None:
        """Display cover art in the reserved space above the info text."""
        if not self._thumb_path or not self._overlay:
            return
        try:
            cols, rows = os.get_terminal_size()
            ov_w = int(cols * 0.7)
            ov_h = int(rows * 0.6)
            ov_y = (rows - ov_h) // 2
            ov_x = (cols - ov_w) // 2

            # center image horizontally in overlay, place at top (inside border)
            img_row = ov_y + 2  # skip border + title line
            img_col = ov_x + (ov_w // 2) - 10  # roughly centered

            tty_fd = os.open("/dev/tty", os.O_WRONLY)
            os.write(tty_fd, f"\x1b7\x1b[{img_row};{img_col}H".encode())
            os.close(tty_fd)

            _kitty_display_image(self._thumb_path, cols=self._img_rows * 2, rows=self._img_rows)

            tty_fd = os.open("/dev/tty", os.O_WRONLY)
            os.write(tty_fd, b"\x1b8")
            os.close(tty_fd)
        except Exception:
            pass

    def _close_overlay(self) -> None:
        if self._thumb_path:
            if _in_kitty():
                _kitty_clear_images()
            try:
                os.unlink(self._thumb_path)
            except Exception:
                pass
            self._thumb_path = None
        self._overlay = None
        self._overlay_info = None
        self._loop.widget = self._frame
        self._status.set_text(("status", "/ search  j/k nav  l info  d download  tab type  q quit"))

    # --- Download ---

    def _on_download(self) -> None:
        if self._overlay and self._overlay_info:
            url = self._overlay_info.get("url", "")
            title = self._overlay_info.get("title", "track")
            self._close_overlay()
        else:
            result = self._get_selected_result()
            if not result:
                return
            vid = result.get("videoId")
            if not vid:
                self._status.set_text(("dim", "only songs can be downloaded"))
                return
            url = f"https://music.youtube.com/watch?v={vid}"
            title = result.get("title", "track")

        self._start_download(url, title)

    def _start_download(self, url: str, title: str) -> None:
        self._progress_text.set_text(("accent", f" {title} "))
        self._progress_bar.set_completion(0)
        self._show_progress(True)

        def progress_hook(d: dict) -> None:
            status = d.get("status", "")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                if total:
                    pct = int(downloaded / total * 100)
                    self._invoke(lambda pct=pct: self._progress_bar.set_completion(pct))
            elif status == "finished":
                self._invoke(lambda: self._progress_bar.set_completion(100))

        def _do_download():
            try:
                result = download.download_audio(
                    url, output_dir="~/Music", fmt="best", progress_callback=progress_hook,
                )
                self._invoke(lambda: self._status.set_text(("success", f"downloaded {result.get('title', 'track')}")))
            except Exception as e:
                self._invoke(lambda: self._status.set_text(("error", f"download failed: {e}")))
            finally:
                self._invoke(lambda: self._show_progress(False))

        threading.Thread(target=_do_download, daemon=True).start()

    def _show_progress(self, visible: bool) -> None:
        footer_widgets = [urwid.Divider("─")]
        if visible:
            footer_widgets.append(self._progress_row)
        footer_widgets.append(self._status)
        self._frame.contents["footer"] = (urwid.Pile(footer_widgets), None)

    # --- Helpers ---

    def _get_selected_result(self) -> dict[str, Any] | None:
        if not self._current_results:
            return None
        try:
            focus_pos = self._result_walker.focus
            if focus_pos is not None and 0 <= focus_pos < len(self._current_results):
                return self._current_results[focus_pos]
        except Exception:
            pass
        return None
