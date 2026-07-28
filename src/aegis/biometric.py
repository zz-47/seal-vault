from __future__ import annotations

import ctypes
import hmac
import logging
import sys
import threading
import time
from typing import Optional

from aegis._errors import PermissionError, ConfigError

logger = logging.getLogger("seal.biometric")


def _hide_console():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass


def _show_console():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 5)
    except Exception:
        pass


def _bring_dialog_to_foreground(stop_event, timeout=30):
    known_classes = ["Windows.Security.Credentials.UI.UserConsentVerifier",
                     "ApplicationManager_DesktopShellWindow",
                     "#32770"]
    known_titles = ["Windows Security", None]
    start = time.monotonic()
    while not stop_event.is_set():
        if time.monotonic() - start > timeout:
            return
        for cls in known_classes:
            for title in known_titles:
                try:
                    hwnd = ctypes.windll.user32.FindWindowW(cls, title)
                    if hwnd:
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                        ctypes.windll.user32.BringWindowToTop(hwnd)
                        return
                except Exception:
                    pass
        time.sleep(0.05)


_SERVICE_NAME = "seal-vault"


class BiometricUnlock:

    def __init__(self, vault_id: str = "default"):
        self._vault_id = vault_id
        self._keyring = None
        self._has_biometric = False
        self._init_keyring()

    def _init_keyring(self) -> None:
        try:
            import keyring
            self._keyring = keyring
        except ImportError:
            logger.warning(
                "keyring library not installed. "
                "Install with: pip install keyring"
            )
            return

        try:
            from pylocalauth import authenticate
            self._has_biometric = True
            self._authenticate = authenticate
        except ImportError:
            logger.info(
                "pylocalauth not installed. Biometric unlock unavailable. "
                "Install with: pip install pylocalauth"
            )
            self._authenticate = None

    def is_configured(self) -> bool:
        if self._keyring is None:
            return False
        return self._keyring.get_password(_SERVICE_NAME, self._vault_id) is not None

    def setup(self, passphrase: str) -> None:
        if self._keyring is None:
            raise ConfigError(
                "keyring library not installed.",
                hint="Install with: pip install keyring",
                code="keyring_not_installed",
            )
        self._keyring.set_password(_SERVICE_NAME, self._vault_id, passphrase)

    def unlock(self, console=True) -> Optional[str]:
        if self._keyring is None:
            raise ConfigError(
                "keyring library not installed.",
                hint="Install with: pip install keyring",
                code="keyring_not_installed",
            )

        if self._has_biometric and self._authenticate is not None:
            message = f"Authenticate to unlock vault '{self._vault_id}'"
            if console:
                _hide_console()
            stop = threading.Event()
            fg_thread = threading.Thread(target=_bring_dialog_to_foreground,
                                         args=(stop,), daemon=True)
            fg_thread.start()
            try:
                ok = self._authenticate(message=message)
            finally:
                stop.set()
                if console:
                    _show_console()
            if not ok:
                raise PermissionError(
                    "Biometric authentication failed.",
                    hint="Try again or use --passphrase flag.",
                    code="biometric_failed",
                )

        else:
            if sys.stdin.isatty():
                import getpass
                pw = getpass.getpass(
                    f"Enter master password for vault '{self._vault_id}': "
                )
                stored = self._keyring.get_password(_SERVICE_NAME, self._vault_id)

                if stored and hmac.compare_digest(stored, pw):
                    return stored
                raise PermissionError(
                    "Incorrect master password.",
                    hint="Use --passphrase flag or enroll fingerprint.",
                    code="passphrase_wrong",
                )
            else:
                raise PermissionError(
                    "No biometric available and stdin is not a TTY.",
                    hint="Use --passphrase flag.",
                    code="no_auth_method",
                )

        passphrase = self._keyring.get_password(_SERVICE_NAME, self._vault_id)
        if passphrase is None:
            raise PermissionError(
                f"No passphrase stored for vault '{self._vault_id}'.",
                hint="Run: seal biometric enroll -P <vault-path> -p <passphrase>",
                code="no_stored_passphrase",
            )
        return passphrase

    def remove(self) -> bool:
        if self._keyring is None:
            return False
        try:
            self._keyring.delete_password(_SERVICE_NAME, self._vault_id)
            return True
        except self._keyring.errors.PasswordDeleteError:
            return False
