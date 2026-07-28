from __future__ import annotations

import json
import os
import time
from pathlib import Path


def _get_seal_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "Seal"
    return Path.home() / ".seal"


_CONFIG_DIR = _get_seal_dir()
_CONFIG_FILE = _CONFIG_DIR / "vaults.json"


def _default_vault_dir() -> Path:
    return _CONFIG_DIR / "vaults"


def _ensure_config_dir() -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_registry() -> list[dict]:
    if not _CONFIG_FILE.exists():
        return []
    try:
        data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data.get("vaults", [])
        return []
    except (json.JSONDecodeError, OSError):
        return []


def save_registry(vaults: list[dict]) -> None:
    _ensure_config_dir()
    _CONFIG_FILE.write_text(
        json.dumps({"vaults": vaults}, indent=2, separators=(",", ":")),
        encoding="utf-8",
    )


def register_vault(name: str, path: str) -> None:
    vaults = load_registry()
    for v in vaults:
        if v["name"] == name:
            v["path"] = str(Path(path).resolve())
            v["last_used"] = time.time()
            save_registry(vaults)
            return
    vaults.append({
        "name": name,
        "path": str(Path(path).resolve()),
        "last_used": time.time(),
    })
    save_registry(vaults)


def unregister_vault(name: str) -> bool:
    vaults = load_registry()
    before = len(vaults)
    vaults = [v for v in vaults if v["name"] != name]
    if len(vaults) == before:
        return False
    save_registry(vaults)
    return True


def get_vault_path(name: str) -> str | None:
    for v in load_registry():
        if v["name"] == name:
            return v["path"]
    return None


def touch_vault(name: str) -> None:
    vaults = load_registry()
    for v in vaults:
        if v["name"] == name:
            v["last_used"] = time.time()
            save_registry(vaults)
            return
