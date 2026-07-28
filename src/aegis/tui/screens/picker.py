from __future__ import annotations

import json
import shutil
from pathlib import Path

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static, Button, Label, Input
from textual.containers import Vertical, Horizontal
from textual import on
from textual.binding import Binding
from textual.screen import ModalScreen


class RemoveVaultConfirmScreen(ModalScreen):
    """Confirm vault removal — deletes all files from disk."""

    CSS = """
    RemoveVaultConfirmScreen {
        align: center middle;
    }
    #remove-box {
        width: 50;
        height: auto;
        padding: 2 4;
        border: thick $warning;
        background: $surface;
    }
    #remove-box Label {
        width: 100%;
        text-align: center;
        margin-bottom: 1;
    }
    #confirm-remove-btn {
        width: 100%;
        margin-top: 1;
    }
    #cancel-remove-btn {
        width: 100%;
        margin-top: 1;
    }
    """

    def __init__(self, vault_name: str, vault_path: str, **kwargs):
        super().__init__(**kwargs)
        self.vault_name = vault_name
        self.vault_path = vault_path

    def compose(self) -> ComposeResult:
        with Vertical(id="remove-box"):
            yield Label("[bold yellow]Delete Vault[/]")
            yield Label(
                f"Delete [bold]{self.vault_name}[/]?\n[dim]All vault files will be permanently deleted. This cannot be undone.[/]"
            )
            yield Button("Yes, delete", id="confirm-remove-btn", variant="warning")
            yield Button("Cancel", id="cancel-remove-btn", variant="default")

    @on(Button.Pressed, "#confirm-remove-btn")
    def confirm_remove(self):
        self.dismiss(True)

    @on(Button.Pressed, "#cancel-remove-btn")
    def cancel_remove(self):
        self.dismiss(False)


class VaultPickerScreen(Screen):
    """Select a vault from the registry."""

    CSS = """
    VaultPickerScreen { padding: 1 2; }
    #name-input { width: 100%; margin-bottom: 1; }
    #path-input { width: 100%; margin-bottom: 1; }
    #vault-table { width: 100%; height: 1fr; }
    .btn-row { height: auto; margin-bottom: 1; }
    .btn-row Button { margin-right: 1; }
    #status-bar {
        dock: bottom;
        height: 1;
        padding: 0 1;
        background: $accent;
        color: $text;
    }
    """

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("ctrl+t", "tools", "Encrypt"),
        Binding("ctrl+h", "help", "Help"),
    ]

    def compose(self) -> ComposeResult:
        yield Label("[bold]Vaults[/]")
        with Horizontal():
            yield Input(placeholder="Vault name", id="name-input")
            yield Input(placeholder="Vault path", id="path-input")
        with Horizontal(classes="btn-row"):
            yield Button("Create", id="create-btn", variant="success")
            yield Button("Add", id="add-btn", variant="primary")
            yield Button("Remove", id="remove-btn", variant="warning")
            yield Button("Encrypt", id="encrypt-btn", variant="default")
            yield Button("Help", id="help-btn", variant="default")
            yield Button("Open", id="open-btn", variant="default")
        yield DataTable(id="vault-table")
        yield Static("Esc Back  |  Ctrl+T Encrypt  |  Ctrl+H Help  |  Create new vault or Add existing", id="status-bar")

    def _scan_default_dir(self):
        from aegis.vault_registry import load_registry, register_vault, _default_vault_dir

        default_dir = _default_vault_dir()
        if not default_dir.is_dir():
            return
        known = {v["name"] for v in load_registry()}
        for subdir in default_dir.iterdir():
            if subdir.is_dir() and (subdir / "keys" / "manifest.enc").exists():
                name = subdir.name
                if name not in known:
                    register_vault(name, str(subdir))

    def on_mount(self):
        table = self.query_one("#vault-table", DataTable)
        table.add_columns("Name", "Path", "Last Used")
        self._scan_default_dir()
        self._load_registry()

    def on_screen_resume(self):
        self._load_registry()

    def _load_registry(self):
        from aegis.vault_registry import load_registry
        table = self.query_one("#vault-table", DataTable)
        table.clear()
        entries = load_registry()
        for v in entries:
            ts = ""
            if v.get("last_used"):
                import time
                ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(v["last_used"]))
            exists = Path(v["path"]).exists()
            name_display = v["name"]
            path_display = v["path"]
            table.add_row(name_display, path_display, ts)
        self.query_one("#status-bar", Static).update(
            f"{len(entries)} vault(s) registered"
        )

    @on(Button.Pressed, "#create-btn")
    def create_vault(self):
        from aegis.tui.screens.create_vault import CreateVaultScreen

        def on_created(result):
            if result is not None:
                self.app.vault_path = result
                self._load_registry()
                self.app._on_vault_picked(result)

        self.app.push_screen(CreateVaultScreen(), on_created)

    @on(Button.Pressed, "#add-btn")
    def add_vault(self):
        from aegis.vault_registry import register_vault

        name = self.query_one("#name-input", Input).value.strip()
        path = self.query_one("#path-input", Input).value.strip()
        if not name or not path:
            self.notify("Enter both name and path", severity="warning")
            return
        p = Path(path)
        if not (p / "keys" / "manifest.enc").exists():
            self.notify(f"No vault found at {path}", severity="warning")
            return
        register_vault(name, path)
        self.notify(f"Registered vault '{name}'", severity="success")
        self.query_one("#name-input", Input).value = ""
        self.query_one("#path-input", Input).value = ""
        self._load_registry()

    @on(Button.Pressed, "#remove-btn")
    def remove_vault(self):
        from aegis.vault_registry import unregister_vault

        table = self.query_one("#vault-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            self.notify("Select a vault first", severity="warning")
            return
        row = table.get_row_at(table.cursor_row)
        name = str(row[0])
        path = str(row[1])

        def on_confirm(result):
            if result:
                unregister_vault(name)
                vpath = Path(path)
                if vpath.exists():
                    shutil.rmtree(vpath)
                self.notify(f"Deleted vault '{name}'", severity="success")
                self._load_registry()

        self.app.push_screen(RemoveVaultConfirmScreen(name, path), on_confirm)

    @on(Button.Pressed, "#open-btn")
    def open_selected(self):
        table = self.query_one("#vault-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            self.notify("Select a vault first", severity="warning")
            return
        row = table.get_row_at(table.cursor_row)
        vault_path = Path(str(row[1]))
        if not vault_path.exists():
            self.notify(f"Vault not found at {vault_path}", severity="error")
            return
        self.dismiss(vault_path)

    @on(DataTable.RowSelected)
    def select_row(self, event):
        table = self.query_one("#vault-table", DataTable)
        if event.row_key is not None:
            row = table.get_row_at(event.row_key)
            if row:
                self.query_one("#name-input", Input).value = str(row[0])
                self.query_one("#path-input", Input).value = str(row[1])

    def action_go_back(self):
        self.app._pop_or_exit()

    def action_tools(self):
        self.app.action_tools()

    def action_help(self):
        self.app.action_help()

    @on(Button.Pressed, "#encrypt-btn")
    def encrypt_file(self):
        self.action_tools()

    @on(Button.Pressed, "#help-btn")
    def help_screen(self):
        self.action_help()
