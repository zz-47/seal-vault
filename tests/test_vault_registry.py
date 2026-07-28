import json
import time
from pathlib import Path

import pytest

from aegis.vault_registry import (
    load_registry,
    save_registry,
    register_vault,
    unregister_vault,
    get_vault_path,
    touch_vault,
)


@pytest.fixture(autouse=True)
def isolated_registry(tmp_path, monkeypatch):
    """Redirect config to a temp dir so tests don't touch ~/.seal."""
    cfg_dir = tmp_path / ".seal"
    cfg_dir.mkdir()
    monkeypatch.setattr("aegis.vault_registry._CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("aegis.vault_registry._CONFIG_FILE", cfg_dir / "vaults.json")
    yield cfg_dir


class TestVaultRegistry:
    def test_load_empty(self):
        assert load_registry() == []

    def test_register_and_load(self, isolated_registry):
        register_vault("work", "/tmp/work-vault")
        entries = load_registry()
        assert len(entries) == 1
        assert entries[0]["name"] == "work"
        assert entries[0]["path"] == str(Path("/tmp/work-vault").resolve())

    def test_register_updates_existing(self, isolated_registry):
        register_vault("work", "/tmp/v1")
        register_vault("work", "/tmp/v2")
        entries = load_registry()
        assert len(entries) == 1
        assert entries[0]["path"] == str(Path("/tmp/v2").resolve())

    def test_unregister(self, isolated_registry):
        register_vault("work", "/tmp/work-vault")
        assert unregister_vault("work") is True
        assert load_registry() == []

    def test_unregister_not_found(self):
        assert unregister_vault("nonexistent") is False

    def test_get_vault_path(self, isolated_registry):
        register_vault("personal", "/tmp/personal-vault")
        path = get_vault_path("personal")
        assert path == str(Path("/tmp/personal-vault").resolve())

    def test_get_vault_path_not_found(self):
        assert get_vault_path("nope") is None

    def test_touch_vault(self, isolated_registry):
        register_vault("work", "/tmp/work-vault")
        before = load_registry()[0]["last_used"]
        time.sleep(0.01)
        touch_vault("work")
        after = load_registry()[0]["last_used"]
        assert after > before

    def test_touch_nonexistent(self):
        touch_vault("nope")

    def test_persistence(self, isolated_registry):
        register_vault("a", "/tmp/a")
        register_vault("b", "/tmp/b")
        entries = load_registry()
        assert len(entries) == 2
        entries2 = load_registry()
        assert entries == entries2

    def test_corrupted_file(self, isolated_registry):
        (isolated_registry / "vaults.json").write_text("not json!!!", encoding="utf-8")
        assert load_registry() == []

    def test_multiple_vaults(self, isolated_registry):
        register_vault("a", "/tmp/a")
        register_vault("b", "/tmp/b")
        register_vault("c", "/tmp/c")
        entries = load_registry()
        assert len(entries) == 3
        names = [v["name"] for v in entries]
        assert names == ["a", "b", "c"]
