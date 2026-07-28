from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import DataTable, Button, Static, Input
from textual.containers import Vertical, Horizontal
from textual import on
from textual.binding import Binding


class FileBrowserScreen(ModalScreen):
    """Browse and select a file or directory."""

    CSS = """
    FileBrowserScreen {
        align: center middle;
    }
    #browser-box {
        width: 70;
        height: 80%;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }
    #dir-input { width: 100%; margin-bottom: 1; }
    #file-table { width: 100%; height: 1fr; }
    .btn-row { width: 100%; height: auto; margin-top: 1; }
    .btn-row Button { margin-right: 1; }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, start_path: str = "", select_folders: bool = False, **kwargs):
        super().__init__(**kwargs)
        self._select_folders = select_folders
        if start_path:
            start = Path(start_path).resolve()
        else:
            desktop = Path.home() / "Desktop"
            start = desktop if desktop.is_dir() else Path.home()
        self._current = start if start.is_dir() else start.parent

    def compose(self) -> ComposeResult:
        title = "Select a folder" if self._select_folders else "Select a file"
        with Vertical(id="browser-box"):
            yield Static(f"[bold]{title}[/]", id="browser-title")
            yield Input(value=str(self._current), id="dir-input")
            yield DataTable(id="file-table", cursor_type="row")
            with Horizontal(classes="btn-row"):
                yield Button("Select", id="select-btn", variant="success")
                yield Button("Cancel", id="cancel-btn", variant="default")

    def on_mount(self):
        table = self.query_one("#file-table", DataTable)
        table.add_columns("Name", "Type", "Size")
        self._populate()

    def _populate(self):
        table = self.query_one("#file-table", DataTable)
        table.clear()
        rows = []
        if self._current != self._current.root:
            rows.append(("..", "DIR", ""))
        children = []
        try:
            children = sorted(self._current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            pass
        for child in children:
            try:
                if child.is_dir():
                    rows.append((child.name, "DIR", ""))
                else:
                    sz = ""
                    try:
                        size = child.stat().st_size
                        sz = f"{size:,} B" if size < 1024 else f"{size/1024:.1f} KB"
                    except OSError:
                        sz = "?"
                    rows.append((child.name, "FILE", sz))
            except OSError:
                rows.append((child.name, "?", "?"))
        for row in rows:
            table.add_row(*row)

    @on(Input.Submitted, "#dir-input")
    def go_to_dir(self):
        path = Path(self.query_one("#dir-input", Input).value)
        if path.is_dir():
            self._current = path
            self._populate()
        else:
            self.notify("Directory not found", severity="warning")

    @on(DataTable.RowSelected)
    def row_selected(self, event):
        table = self.query_one("#file-table", DataTable)
        row = table.get_row(event.row_key)
        name = str(row[0])
        if name == "..":
            self._current = self._current.parent
            self._populate()
            return
        path = self._current / name
        if path.is_dir():
            self._current = path
            self._populate()
        else:
            self.dismiss(str(path))

    @on(Button.Pressed, "#select-btn")
    def select_current(self):
        self.dismiss(str(self._current))

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self):
        self.dismiss(None)

    def action_cancel(self):
        self.dismiss(None)
