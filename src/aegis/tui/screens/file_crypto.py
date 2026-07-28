from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Input, Button, Label, Select
from textual.containers import Vertical, Horizontal
from textual import on
from textual.binding import Binding


class FileCryptoScreen(Screen):
    """Encrypt or decrypt a file using a passphrase."""

    CSS = """
    FileCryptoScreen { padding: 1 2; }
    #crypto-box { width: 70; height: auto; padding: 2 4; border: thick $primary; background: $surface; }
    #crypto-box Label { width: 100%; margin-bottom: 1; }
    #op-select { width: 100%; margin-bottom: 1; }
    .path-row { height: auto; margin-bottom: 1; }
    .path-row Input { width: 1fr; }
    .path-row Button { width: auto; margin-left: 1; }
    #pass-input { width: 100%; margin-bottom: 1; }
    #run-btn { width: 100%; margin-top: 1; }
    #cancel-btn { width: 100%; margin-top: 1; }
    #status-bar {
        dock: bottom;
        height: 1;
        padding: 0 1;
        background: $accent;
        color: $text;
    }
    """

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        with Vertical(id="crypto-box"):
            yield Label("[bold]Encrypt / Decrypt File[/]")
            yield Select(
                [("Encrypt", "encrypt"), ("Decrypt", "decrypt")],
                id="op-select",
                value="encrypt",
                prompt="Operation",
            )
            with Horizontal(classes="path-row"):
                yield Input(placeholder="Source path (e.g. C:\\path\\to\\file.txt)", id="src-input")
                yield Button("Browse", id="src-browse-btn", variant="default")
            with Horizontal(classes="path-row"):
                yield Input(placeholder="Output path", id="dst-input")
                yield Button("Browse", id="dst-browse-btn", variant="default")
            yield Input(password=True, placeholder="Passphrase", id="pass-input")
            yield Button("Run", id="run-btn", variant="success")
            yield Button("Cancel", id="cancel-btn", variant="default")
        yield Static("Esc Back  |  Select operation, enter paths and passphrase, then Run", id="status-bar")

    def on_mount(self):
        pw = getattr(self.app, "passphrase", None)
        if pw:
            self.query_one("#pass-input", Input).value = pw
            self.query_one("#status-bar", Static).update("Esc Back  |  Vault passphrase pre-filled. Enter paths and Run")

    @on(Button.Pressed, "#src-browse-btn")
    def browse_source(self):
        from aegis.tui.screens.file_browser import FileBrowserScreen

        def on_picked(result):
            if result:
                self.query_one("#src-input", Input).value = result

        self.app.push_screen(FileBrowserScreen(), on_picked)

    @on(Button.Pressed, "#dst-browse-btn")
    def browse_dest(self):
        from aegis.tui.screens.file_browser import FileBrowserScreen

        op = self.query_one("#op-select", Select).value
        select_folders = op == "encrypt"

        def on_picked(result):
            if result:
                self.query_one("#dst-input", Input).value = result

        self.app.push_screen(FileBrowserScreen(select_folders=select_folders), on_picked)

    @on(Button.Pressed, "#run-btn")
    def run(self):
        op = self.query_one("#op-select", Select).value
        src = self.query_one("#src-input", Input).value.strip()
        dst = self.query_one("#dst-input", Input).value.strip()
        pw = self.query_one("#pass-input", Input).value

        if not src:
            self.notify("Enter a source path", severity="warning")
            return
        if not dst:
            self.notify("Enter an output path", severity="warning")
            return
        if not pw:
            self.notify("Enter a passphrase", severity="warning")
            return

        src_path = Path(src)
        if not src_path.exists():
            self.notify(f"Source not found: {src}", severity="error")
            return

        dst_path = Path(dst).resolve()

        btn = self.query_one("#run-btn", Button)
        btn.label = "Working..."
        btn.disabled = True
        self._do_work(op, src, str(dst_path), src_path, pw)

    def _do_work(self, op, src, dst_str, src_path, pw):
        try:
            if op == "encrypt":
                from aegis.file_crypto import encrypt_file, encrypt_folder

                if src_path.is_dir():
                    encrypt_folder(src, dst_str, pw)
                else:
                    encrypt_file(src, dst_str, pw)
                self.notify(f"Encrypted {src_path.name}", severity="success")
            else:
                from aegis.file_crypto import decrypt_file, decrypt_archive

                try:
                    decrypt_file(src, dst_str, pw)
                except Exception:
                    try:
                        decrypt_archive(src, dst_str, pw)
                    except Exception as e2:
                        raise Exception(f"Decrypt failed: {e2}")
                self.notify(f"Decrypted {src_path.name}", severity="success")
        except Exception as e:
            self.notify(f"Failed: {e}", severity="error")
        finally:
            btn = self.query_one("#run-btn", Button)
            btn.label = "Run"
            btn.disabled = False

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self):
        self.app.pop_screen()

    def action_go_back(self):
        self.app.pop_screen()
