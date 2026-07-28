from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static, Button, Label
from textual.containers import Vertical, ScrollableContainer
from textual import on
from textual.binding import Binding


class HelpScreen(ModalScreen):
    """Keyboard shortcuts and feature reference."""

    CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-box {
        width: 70;
        height: 80%;
        padding: 2 4;
        border: thick $primary;
        background: $surface;
    }
    #help-box Label {
        width: 100%;
        text-align: center;
        margin-bottom: 1;
    }
    #help-content {
        width: 100%;
        height: 1fr;
    }
    #help-content Static {
        width: 100%;
    }
    #close-help-btn {
        width: 100%;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("h", "close", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-box"):
            yield Label("[bold]Seal Help[/]")
            with ScrollableContainer(id="help-content"):
                yield Static("""
[bold underline]Vault Picker[/]
  Ctrl+T        Open file encrypt/decrypt
  Ctrl+H        Open this help screen
  Ctrl+Q        Quit
  Esc           Go back / exit

[bold underline]Login[/]
  Windows Hello  Click "Unlock with Windows Hello" for fingerprint
  Passphrase     Type master passphrase and press Enter
  Save           Store passphrase for future biometric unlock

[bold underline]Vault Browser[/]
  Ctrl+N        Create a new entry
  Ctrl+E        Edit selected entry
  Ctrl+D        Delete selected entry
  Ctrl+F        Focus search bar
  Ctrl+G        Open password generator
  Ctrl+T        Open file encrypt/decrypt
  Ctrl+V        Verify vault integrity
  Ctrl+R        Open compliance report
  Ctrl+Y        Open canary management
  Ctrl+O        Switch vault (return to picker)
  Ctrl+H        Open this help screen
  Ctrl+Q        Quit (with passphrase confirmation)
  Esc           Return to vault picker (with passphrase confirmation)

[bold underline]Password Generator (Ctrl+G)[/]
  Set length (8-64), toggle symbols
  Regenerate or copy to clipboard

[bold underline]File Encrypt / Decrypt (Ctrl+T)[/]
  Choose Encrypt or Decrypt from dropdown
  Enter source path or click Browse
  Enter output path or click Browse
  Passphrase pre-filled from vault (if unlocked)
  Click Run to execute

[bold underline]Compliance Reports (Ctrl+R)[/]
  SOC 2, HIPAA, GDPR, ISO 27001
  One-click export as Markdown or JSON

[bold underline]Canary Management (Ctrl+Y)[/]
  Deploy decoy files to detect ransomware
  Check canary status
  Remove all canary files

[bold underline]CLI (command line)[/]
  seal init -P <path> -p <pass>     Create vault
  seal save -P <path> ...            Store data
  seal load -P <path> ...            View data
  seal list -P <path>               List entries
  seal encrypt/decrypt ...           File encryption
  seal doctor -P <path>             Health check
  seal --help                        All commands
                """)
            yield Button("Close", id="close-help-btn", variant="primary")

    @on(Button.Pressed, "#close-help-btn")
    def close(self):
        self.app.pop_screen()

    def action_close(self):
        self.app.pop_screen()
