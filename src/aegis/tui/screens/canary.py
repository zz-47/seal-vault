from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import DataTable, Static, Button, Label, Input
from textual.containers import Vertical, Horizontal
from textual.screen import Screen, ModalScreen
from textual import on
from textual.binding import Binding


class CanaryRemoveConfirmScreen(ModalScreen):
    """Require passphrase before removing all canaries."""

    CSS = """
    CanaryRemoveConfirmScreen {
        align: center middle;
    }
    #remove-box { width: 50; height: auto; padding: 2 4; border: thick $error; background: $surface; }
    #remove-box Label { width: 100%; text-align: center; margin-bottom: 1; }
    #remove-passphrase { width: 100%; margin-top: 1; }
    #confirm-btn { width: 100%; margin-top: 1; }
    #cancel-btn { width: 100%; margin-top: 1; }
    """
    def compose(self) -> ComposeResult:
        with Vertical(id="remove-box"):
            yield Label("[bold red]Remove All Canaries[/]")
            yield Label("Remove all canary files?\n[dim]This requires passphrase verification.[/]")
            yield Input(password=True, placeholder="Enter passphrase to confirm", id="remove-passphrase")
            yield Button("Remove", id="confirm-btn", variant="error")
            yield Button("Cancel", id="cancel-btn", variant="default")
    
    @on(Button.Pressed, "#confirm-btn")
    def confirm_remove(self):
        entered = self.query_one("#remove-passphrase", Input).value
        if entered != self.app.passphrase:
            self.notify("Wrong passphrase", severity="error")
            return
        self.dismiss(True)

    @on(Button.Pressed, "#cancel-btn")
    def cancel_remove(self):
        self.dismiss(False)

    @on(Input.Submitted, "#remove-passphrase")
    def on_passphrase_submitted(self):
        self.confirm_remove()

class CanaryScreen(Screen):
    """Canary deploy / check / remove / status."""

    CSS = """
    CanaryScreen { padding: 1 2; }
    #canary-table { width: 100%; height: 1fr; }
    #status-bar {
        dock: bottom;
        height: 1;
        padding: 0 1;
        background: $accent;
        color: $text;
    }
    .btn-row { height: auto; margin-bottom: 1; }
    .btn-row Button { margin-right: 1; }
    """

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Label("[bold]Canary Management[/]")
        with Horizontal(classes="btn-row"):
            yield Button("Deploy Canaries", id="deploy-btn", variant="success")
            yield Button("Check All", id="check-btn", variant="primary")
            yield Button("Remove All", id="remove-btn", variant="error")
        yield DataTable(id="canary-table")
        yield Static("Esc Back", id="status-bar")

    def on_mount(self):
        table = self.query_one("#canary-table", DataTable)
        table.add_columns("Name", "Path", "Exists", "Entropy", "Status")
        self._load_status()

    def _load_status(self):
        app = self.app
        canary = getattr(app, '_canary', None)
        if canary is None:
            try:
                from aegis.canary import CanaryManager
                canary = CanaryManager(app.base_path)
                app._canary = canary
            except Exception:
                self.query_one("#status-bar", Static).update("Canary manager unavailable")
                return
        table = self.query_one("#canary-table", DataTable)
        table.clear()
        for entry in canary.status():
            exists = "Yes" if entry["exists"] else "MISSING"
            entropy = f"{entry['entropy']:.2f}"
            table.add_row(entry["name"], entry["path"], exists, entropy, "OK")
        self.query_one("#status-bar", Static).update(
            f"{len(canary.status())} canaries tracked"
        )

    @on(Button.Pressed, "#deploy-btn")
    def deploy(self):
        canary = getattr(self.app, '_canary', None)
        if canary is None:
            self.notify("Canary manager unavailable", severity="error")
            return
        new = canary.deploy()
        self.notify(f"Deployed {len(new)} canary files", severity="success")
        self._load_status()

    @on(Button.Pressed, "#check-btn")
    def check(self):
        canary = getattr(self.app, '_canary', None)
        if canary is None:
            self.notify("Canary manager unavailable", severity="error")
            return
        result = canary.check_all()
        if result.has_alerts:
            parts = []
            if result.triggered:
                names = ", ".join(c.name for c, _, _ in result.triggered)
                parts.append(f"Modified: {names}")
            if result.missing:
                names = ", ".join(c.name for c in result.missing)
                parts.append(f"Missing: {names}")
            self.notify(
                "\n".join(parts),
                title="Canary Alert",
                severity="error",
            )
        else:
            self.notify("All canaries clean", severity="success")
        self._load_status()

    @on(Button.Pressed, "#remove-btn")
    def remove(self):
        def on_confirm(result):
            if result:
                canary = getattr(self.app, '_canary', None)
                if canary is None:
                    self.notify("Canary manager unavailable", severity="error")
                    return
                count = canary.remove()
                self.notify(f"Removed {count} canary files", severity="success")
                self._load_status()
        self.app.push_screen(CanaryRemoveConfirmScreen(), on_confirm)

    def action_go_back(self):
        self.app._pop_or_exit()
