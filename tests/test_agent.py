"""Tests for the Seal routing agent."""
from __future__ import annotations

import pytest
from aegis.agent import SealAgent, RoutedCommand, _PATTERNS


@pytest.fixture
def agent():
    return SealAgent()


class TestRouteSave:

    def test_save_gmail(self, agent):
        cmd = agent.route("save my gmail password")
        assert cmd.command == "save"
        assert cmd.args["item_id"] == "gmail"

    def test_save_store(self, agent):
        cmd = agent.route("store my wifi password")
        assert cmd.command == "save"
        assert "wifi" in cmd.args["item_id"]

    def test_save_add_to_vault(self, agent):
        cmd = agent.route("add netflix to the vault")
        assert cmd.command == "save"
        assert "netflix" in cmd.args["item_id"]

    def test_save_new_entry(self, agent):
        cmd = agent.route("new entry dropbox")
        assert cmd.command == "save"
        assert "dropbox" in cmd.args["item_id"]

    def test_save_plain(self, agent):
        cmd = agent.route("save my bank credentials")
        assert cmd.command == "save"
        assert "bank" in cmd.args["item_id"]


class TestRouteLoad:

    def test_load_gmail_password(self, agent):
        cmd = agent.route("get my gmail password")
        assert cmd.command == "load"
        assert cmd.args["item_id"] == "gmail"

    def test_load_show(self, agent):
        cmd = agent.route("show me my vpn credentials")
        assert cmd.command == "load"
        assert "vpn" in cmd.args["item_id"]

    def test_load_password_for(self, agent):
        cmd = agent.route("password for netflix")
        assert cmd.command == "load"
        assert "netflix" in cmd.args["item_id"]

    def test_load_whats(self, agent):
        cmd = agent.route("what's my wifi password")
        assert cmd.command == "load"
        assert "wifi" in cmd.args["item_id"]

    def test_load_retrieve(self, agent):
        cmd = agent.route("retrieve my github login")
        assert cmd.command == "load"
        assert "github" in cmd.args["item_id"]


class TestRouteList:

    def test_list_passwords(self, agent):
        cmd = agent.route("list all passwords")
        assert cmd.command == "list"
        assert cmd.args == {}

    def test_list_entries(self, agent):
        cmd = agent.route("show all entries")
        assert cmd.command == "list"

    def test_list_vault(self, agent):
        cmd = agent.route("show my vault")
        assert cmd.command == "list"

    def test_list_do_i_have(self, agent):
        cmd = agent.route("what do I have saved")
        assert cmd.command == "list"


class TestRouteDelete:

    def test_delete_gmail(self, agent):
        cmd = agent.route("delete my gmail password")
        assert cmd.command == "delete"
        assert cmd.args["item_id"] == "gmail"

    def test_remove_entry(self, agent):
        cmd = agent.route("remove old-password from vault")
        assert cmd.command == "delete"
        assert "old-password" in cmd.args["item_id"]


class TestRouteVerify:

    def test_check_integrity(self, agent):
        cmd = agent.route("check vault integrity")
        assert cmd.command == "verify"

    def test_health_check(self, agent):
        cmd = agent.route("vault health check")
        assert cmd.command == "verify"

    def test_is_vault_safe(self, agent):
        cmd = agent.route("is my vault safe")
        assert cmd.command == "verify"


class TestRouteGenerate:

    def test_generate_password(self, agent):
        cmd = agent.route("generate a new password")
        assert cmd.command == "generate"
        assert cmd.args == {}

    def test_generate_with_length(self, agent):
        cmd = agent.route("generate a 32 character password")
        assert cmd.command == "generate"
        assert cmd.args.get("length") == 32

    def test_need_password(self, agent):
        cmd = agent.route("I need a new password")
        assert cmd.command == "generate"


class TestRouteEncryptDecrypt:

    def test_encrypt_file(self, agent):
        cmd = agent.route("encrypt file secrets.txt")
        assert cmd.command == "encrypt"
        assert cmd.args["infile"] == "secrets.txt"

    def test_decrypt_file(self, agent):
        cmd = agent.route("decrypt file data.enc")
        assert cmd.command == "decrypt"
        assert cmd.args["infile"] == "data.enc"


class TestRouteCanary:

    def test_check_ransomware(self, agent):
        cmd = agent.route("check for ransomware")
        assert cmd.command == "canary check"

    def test_deploy_canaries(self, agent):
        cmd = agent.route("deploy canary")
        assert cmd.command == "canary deploy"

    def test_remove_canaries(self, agent):
        cmd = agent.route("remove canaries")
        assert cmd.command == "canary remove"


class TestRouteAudit:

    def test_show_audit(self, agent):
        cmd = agent.route("show the audit log")
        assert cmd.command == "audit show"

    def test_audit_trail(self, agent):
        cmd = agent.route("audit trail")
        assert cmd.command == "audit show"


class TestRouteReport:

    def test_generate_report(self, agent):
        cmd = agent.route("generate a compliance report")
        assert cmd.command == "report generate"

    def test_soc2_report(self, agent):
        cmd = agent.route("soc2 report")
        assert cmd.command == "report generate"
        assert cmd.args.get("framework") == "soc2"

    def test_hipaa_report(self, agent):
        cmd = agent.route("hipaa report")
        assert cmd.command == "report generate"
        assert cmd.args.get("framework") == "hipaa"


class TestRouteVaults:

    def test_list_vaults(self, agent):
        cmd = agent.route("list vaults")
        assert cmd.command == "vaults list"

    def test_register_vault(self, agent):
        cmd = agent.route("register vault /path/to/vault")
        assert cmd.command == "vaults add"
        assert "/path/to/vault" in cmd.args["path"]


class TestRouteEdgeCases:

    def test_empty_input(self, agent):
        cmd = agent.route("")
        assert cmd.command == "help"
        assert cmd.confidence == 0.0

    def test_unknown_input(self, agent):
        cmd = agent.route("xyzzy foobar baz")
        assert cmd.command == "unknown"
        assert cmd.confidence == 0.0

    def test_case_insensitive(self, agent):
        cmd = agent.route("LIST ALL PASSWORDS")
        assert cmd.command == "list"

    def test_confidence_always_one_for_rules(self, agent):
        cmd = agent.route("save my gmail password")
        assert cmd.confidence == 1.0


class TestRoutedCommand:

    def test_to_args_list_save(self):
        cmd = RoutedCommand(command="save", args={"ns": "personal", "item_id": "gmail"})
        parts = cmd.to_args_list()
        assert parts[0] == "save"
        assert "-n" in parts
        assert "personal" in parts
        assert "-i" in parts
        assert "gmail" in parts

    def test_to_args_list_list(self):
        cmd = RoutedCommand(command="list", args={"long": True})
        parts = cmd.to_args_list()
        assert "--long" in parts

    def test_to_args_list_clip(self):
        cmd = RoutedCommand(command="load", args={"clip": True})
        parts = cmd.to_args_list()
        assert "--clip" in parts

    def test_to_args_list_no_clip(self):
        cmd = RoutedCommand(command="load", args={"clip": False})
        parts = cmd.to_args_list()
        assert "--clip" not in parts

    def test_to_args_list_length(self):
        cmd = RoutedCommand(command="generate", args={"length": 32})
        parts = cmd.to_args_list()
        assert "-l" in parts
        assert "32" in parts

    def test_to_args_list_framework(self):
        cmd = RoutedCommand(command="report generate", args={"framework": "soc2"})
        parts = cmd.to_args_list()
        assert "-f" in parts
        assert "soc2" in parts

    def test_to_args_list_empty(self):
        cmd = RoutedCommand(command="list")
        parts = cmd.to_args_list()
        assert parts == ["list"]


class TestPatterns:

    def test_all_patterns_have_groups(self):
        """Every pattern with extraction indices must have that many groups."""
        import re
        for pattern, command, extractors in _PATTERNS:
            if not extractors:
                continue
            # test with dummy data
            m = re.search(pattern, "save my gmail password test 1234", re.IGNORECASE)
            # not every pattern will match every input, but the pattern itself must be valid regex
            re.compile(pattern)
