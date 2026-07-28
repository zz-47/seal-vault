from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Input, Button, Label, Select, Switch
from textual.containers import Vertical, Horizontal
from textual import on
from textual.binding import Binding

from aegis.vault_registry import _default_vault_dir


class CreateVaultScreen(Screen):
    """Create a new encrypted vault."""

    CSS = """
    CreateVaultScreen { padding: 1 2; }
    #create-box {
        width: 60;
        height: auto;
        padding: 2 4;
        border: thick $primary;
        background: $surface;
    }
    #create-box Label {
        width: 100%;
        margin-bottom: 1;
    }
    #path-input, #passphrase-input, #confirm-input {
        width: 100%;
        margin-bottom: 1;
    }
    #cipher-select { width: 100%; margin-bottom: 1; }
    #strength-label { width: 100%; min-height: 1; }
    #bio-row { width: 100%; margin-bottom: 1; height: auto; }
    #bio-row Switch { width: auto; margin-right: 1; }
    #bio-row Label { width: 1fr; margin-bottom: 0; }
    #create-btn { width: 100%; margin-top: 1; }
    #cancel-btn { width: 100%; margin-top: 1; }
    """

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._bio_available = self._check_biometric()

    def _check_biometric(self) -> bool:
        try:
            from aegis.biometric import BiometricUnlock
            bio = BiometricUnlock()
            return bio._has_biometric
        except Exception:
            return False

    def on_mount(self):
        default = _default_vault_dir() / "my-vault"
        self.query_one("#path-input", Input).value = str(default)

    def compose(self) -> ComposeResult:
        with Vertical(id="create-box"):
            yield Label("[bold]Create New Vault[/]")
            yield Input(placeholder="Vault path", id="path-input")
            yield Input(password=True, placeholder="Master passphrase", id="passphrase-input")
            yield Static("", id="strength-label")
            yield Input(password=True, placeholder="Confirm passphrase", id="confirm-input")
            yield Select(
                [("AES-256-GCM", "aes-gcm"), ("ChaCha20-Poly1305", "chacha20")],
                id="cipher-select",
                value="aes-gcm",
                prompt="Encryption algorithm",
            )
            if self._bio_available:
                with Horizontal(id="bio-row"):
                    yield Switch(id="bio-switch")
                    yield Label("Save passphrase for Windows Hello unlock")

            yield Button("Create Vault", id="create-btn", variant="success")
            yield Button("Cancel", id="cancel-btn", variant="default")

    @on(Input.Changed, "#passphrase-input")
    def on_passphrase_changed(self, event: Input.Changed):
        pw = event.value
        if not pw:
            self.query_one("#strength-label", Static).update("")
            return
        warnings = []
        if len(pw) < 8:
            warnings.append("shorter than 8 characters")
        if len(pw) < 12:
            warnings.append("consider 12+ characters")
        if pw.lower() == pw and pw.isalpha():
            warnings.append("no uppercase")
        if pw.isalnum() and not any(ch in pw for ch in "!@#$%^&*()-_+=[]{}|;':\",./<>?"):
            warnings.append("no special chars")
        common = {"password", "123456", "qwerty", "letmein", "admin", "welcome"}
        if pw.lower() in common:
            warnings.append("commonly used password")
        if not warnings:
            self.query_one("#strength-label", Static).update("[green]Strong[/]")
        else:
            self.query_one("#strength-label", Static).update(f"[yellow]Weak:[/] {'; '.join(warnings)}")

    @on(Button.Pressed, "#create-btn")
    def create_vault(self):
        from aegis.crypt_storage import AegisVault
        from aegis.vault_registry import register_vault

        path_str = self.query_one("#path-input", Input).value.strip()
        pw = self.query_one("#passphrase-input", Input).value
        confirm = self.query_one("#confirm-input", Input).value
        cipher = self.query_one("#cipher-select", Select).value

        if not path_str:
            self.notify("Enter a vault path", severity="warning")
            return
        if not pw:
            self.notify("Enter a passphrase", severity="warning")
            return
        if pw != confirm:
            self.notify("Passphrases do not match", severity="error")
            return

        vault_dir = Path(path_str)
        vault_marker = vault_dir / "keys" / "manifest.enc"
        if vault_marker.exists():
            try:
                AegisVault(path_str, pw, cipher_suite=cipher)
                self.notify("Existing vault opened with that passphrase", severity="info")
                name = vault_dir.name
                register_vault(name, path_str)
                self.dismiss(vault_dir)
                return
            except Exception:
                self.notify("A vault already exists here with a different passphrase", severity="error")
                return

        try:
            AegisVault(path_str, pw, cipher_suite=cipher)
        except Exception as e:
            self.notify(f"Failed to create vault: {e}", severity="error")
            return

        name = vault_dir.name
        register_vault(name, path_str)

        if self._bio_available and self.query_one("#bio-switch").value:
            try:
                from aegis.biometric import BiometricUnlock
                bio = BiometricUnlock()
                bio.setup(pw)
                self.notify("Passphrase saved for Windows Hello", severity="success")
            except Exception as e:
                self.notify(f"Biometric setup skipped: {e}", severity="warning")

        self.notify(f"Vault created at {vault_dir.resolve()}", severity="success")
        self.dismiss(vault_dir)

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self):
        self.dismiss(None)

    def action_go_back(self):
        self.dismiss(None)
