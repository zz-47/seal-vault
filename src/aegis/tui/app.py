from __future__ import annotations

from pathlib import Path

from textual.app import App
from textual.binding import Binding

from aegis.tui.screens.login import LoginScreen
from aegis.tui.screens.vault import VaultScreen
from aegis._errors import AegisError
from aegis.tui.screens.picker import VaultPickerScreen
from aegis.vault_registry import _default_vault_dir


class SealApp(App):
    """Seal TUI — interactive vault browser."""

    TITLE = "Seal — Local Vault"
    SUB_TITLE = "Encrypted password vault"
    CSS_PATH = None
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+v", "verify", "Verify"),
        Binding("ctrl+r", "report", "Report"),
        Binding("ctrl+y", "canary", "Canary"),
        Binding("ctrl+o", "open_vault", "Open Vault"),
        Binding("ctrl+t", "tools", "Tools"),
        Binding("ctrl+h", "help", "Help"),
    ]

    def __init__(self, vault_path=None, **kwargs):
        super().__init__(**kwargs)
        self.vault_path = vault_path
        self.vault = None
        self.passphrase = None

    def on_mount(self):
        if self.vault_path:
            self.push_screen(LoginScreen(), self._on_login_result)
        else:
            from aegis.tui.screens.picker import VaultPickerScreen
            self.push_screen(VaultPickerScreen(), self._on_vault_picked)

    def _pop_or_exit(self):
        """Pop the current screen, or exit the app if it is the last user screen."""
        from aegis.tui.screens.picker import VaultPickerScreen
        if len(self.screen_stack) <= 1 or isinstance(self.screen, VaultPickerScreen):
            self.exit()
        else:
            self.pop_screen()

    def _pop_to_picker(self):
        """Return to the vault picker, or push a new one if none is in the stack."""
        from aegis.tui.screens.picker import VaultPickerScreen
        has_picker = any(isinstance(s, VaultPickerScreen) for s in self.screen_stack)
        if has_picker:
            while len(self.screen_stack) > 1:
                if isinstance(self.screen, VaultPickerScreen):
                    break
                self.pop_screen()
        else:
            self.vault = None
            self.passphrase = None
            # Pop all user screens, leave Textual's internal _default screen
            while len(self.screen_stack) > 1:
                self.pop_screen()
            self.push_screen(VaultPickerScreen(), self._on_vault_picked)

    def _on_vault_picked(self, result):
        if result is None:
            self.exit()
            return
        self.vault_path = result
        self.push_screen(LoginScreen(), self._on_login_result)

    def _on_login_result(self, result):
        if not result:
            self.exit()
            return
        try:
            from aegis.audit import AuditLog
            from aegis.canary import CanaryManager
            from aegis.crypt_storage import AegisVault

            path = self.vault_path or _default_vault_dir()
            # Validate passphrase FIRST by opening the vault
            audit = AuditLog(path)
            canary = CanaryManager(path)
            vault = AegisVault(path, result.passphrase, audit_log=audit, canary_manager=canary)
            # Only store passphrase after successful validation
            self.passphrase = result.passphrase
            self.vault = vault
            self.push_screen(VaultScreen())
        except (ValueError, KeyError, AegisError) as e:
            self.notify(f"Wrong passphrase or vault error: {e}", severity="error")
            # Return to picker so user isn't stuck on blank terminal
            self._pop_to_picker()

    @property
    def base_path(self) -> Path:
        """Return the resolved base path of the vault."""
        if self.vault is not None:
            return self.vault._base_path
        return self.vault_path or _default_vault_dir()

    def action_verify(self):
        from aegis.audit import AuditLog
        from aegis.canary import CanaryManager

        if not self.vault:
            return
        try:
            audit = AuditLog(self.base_path)
            chain_ok = audit.verify()
            count = audit.entry_count
        except Exception:
            chain_ok, count = False, 0

        try:
            canary = CanaryManager(self.base_path)
            canary_result = canary.check_all()
        except Exception:
            canary_result = None

        status = "VALID" if chain_ok else "BROKEN"
        if canary_result is None:
            canary_status = "CHECK FAILED"
            severity = "error"
        elif canary_result.is_clean:
            canary_status = "CLEAN"
            severity = "info" if chain_ok else "error"
        else:
            t = len(canary_result.triggered)
            m = len(canary_result.missing)
            parts = []
            if t:
                parts.append(f"{t} triggered")
            if m:
                parts.append(f"{m} missing")
            canary_status = ", ".join(parts)
            severity = "error" if not chain_ok else "warning"

        msg = f"Audit Chain: {status} ({count} entries)\nCanary: {canary_status}"
        self.notify(msg, title="Vault Integrity", severity=severity)

    def action_generate(self):
        from aegis.tui.screens.generator import GeneratorScreen
        self.push_screen(GeneratorScreen())

    def action_new_item(self):
        from aegis.tui.screens.vault import NewItemScreen
        self.push_screen(NewItemScreen())

    def action_report(self):
        from aegis.tui.screens.report import ReportScreen
        self.push_screen(ReportScreen())

    def action_canary(self):
        from aegis.tui.screens.canary import CanaryScreen
        self.push_screen(CanaryScreen())

    def action_quit(self):
        if self.passphrase:
            from aegis.tui.screens.vault import LeaveVaultScreen

            def _on_leave(result):
                if result:
                    self.exit()

            self.push_screen(LeaveVaultScreen(), _on_leave)
        else:
            self.exit()

    def action_open_vault(self):
        self._pop_to_picker()

    def action_tools(self):
        from aegis.tui.screens.file_crypto import FileCryptoScreen
        self.push_screen(FileCryptoScreen())

    def action_help(self):
        from aegis.tui.screens.help_screen import HelpScreen
        self.push_screen(HelpScreen())
