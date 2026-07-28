# Test Suite Documentation — Seal (Aegis Vault)

**252 unit tests across 16 files + 57 production integration tests = 309 total. All pass.**

Run all unit tests:
```bash
python -m pytest tests/ -v
```

Run production integration tests (CLI as real user):
```bash
python production_tests/test.py
```

Run a specific module:
```bash
python -m pytest tests/test_cipher.py -v
```

---

## Test File Index

| # | File | Tests | Module Under Test | Purpose |
|---|------|-------|-------------------|---------|
| 1 | `test_cipher.py` | 12 | `aegis.cipher` | AEAD encrypt/decrypt correctness |
| 2 | `test_key_manager.py` | 14 | `aegis.key_manager` | Key derivation, DEK wrapping, manifest |
| 3 | `test_crypt_storage.py` | 12 | `aegis.crypt_storage` | Vault save/load/delete/list |
| 4 | `test_audit.py` | 7 | `aegis.audit` | Tamper-evident audit log |
| 5 | `test_canary.py` | 15 | `aegis.canary` | Ransomware canary detection |
| 6 | `test_sharing.py` | 5 | `aegis.sharing` | X25519 multi-user key exchange |
| 7 | `test_biometric.py` | 7 | `aegis.biometric` | Biometric/keyring unlock (mocked) |
| 8 | `test_report.py` | 10 | `aegis.report` | Compliance report generation |
| 9 | `test_atomic_write.py` | 8 | `aegis.crypt_storage` | Crash-safe atomic writes |
| 10 | `test_data_leak.py` | 7 | `aegis.crypt_storage` | No plaintext on disk |
| 11 | `test_robustness.py` | 19 | All modules | Attack, corruption, edge cases |
| 12 | `test_cli.py` | 50 | `aegis.cli` | CLI command integration (mocked vault) |
| 13 | `test_file_crypto.py` | 9 | `aegis.file_crypto` | Standalone file encrypt/decrypt |
| 14 | `test_vault_registry.py` | 12 | `aegis.vault_registry` | Multi-vault registry management |
| 15 | `test_agent.py` | 46 | `aegis.agent` | Natural language routing |
| 16 | `test_tui_screens.py` | 19 | `aegis.tui.screens` | TUI screen integration |

---

## Detailed Test Index

### 1. `test_cipher.py` — AEAD Cipher (12 tests)

| Test ID | Test Name | What It Proves |
|---------|-----------|----------------|
| C-01 | `test_generate_key_length` | `generate_key()` returns exactly 32 bytes (AES-256) |
| C-02 | `test_encrypt_decrypt_roundtrip` | Encrypt then decrypt returns original plaintext |
| C-03 | `test_combined_roundtrip` | `encrypt_combined`/`decrypt_combined` roundtrip works |
| C-04 | `test_wrong_key_fails` | Decrypting with wrong key raises `DecryptionError` |
| C-05 | `test_tampered_ciphertext_fails` | Flipping a byte in ciphertext raises `DecryptionError` |
| C-06 | `test_wrong_aad_fails` | Mismatched AAD during decrypt raises `DecryptionError` |
| C-07 | `test_wrong_tag_fails` | Tampered auth tag raises `DecryptionError` |
| C-08 | `test_empty_plaintext` | Encrypting and decrypting `b""` works |
| C-09 | `test_large_plaintext` | 1MB random data roundtrips correctly |
| C-10 | `test_chacha20_roundtrip` | ChaCha20-Poly1305 suite works end-to-end |
| C-11 | `test_invalid_key_size` | Key < 32 bytes raises `LocalStorageError` |
| C-12 | `test_multiple_encryptions_unique_nonces` | Two encryptions produce different nonces |

---

### 2. `test_key_manager.py` — Key Manager (14 tests)

| Test ID | Test Name | What It Proves |
|---------|-----------|----------------|
| KM-01 | `test_derive_master_key` | PBKDF2 produces 32-byte key and stores salt |
| KM-02 | `test_derive_with_custom_salt` | Custom salt derivation produces valid key |
| KM-03 | `test_invalid_salt_size` | Salt < 16 bytes raises `LocalStorageError` |
| KM-04 | `test_generate_dek` | DEK generation returns 32 random bytes |
| KM-05 | `test_wrap_unwrap_roundtrip` | Wrap DEK then unwrap returns original DEK |
| KM-06 | `test_wrong_item_id_fails` | Unwrap with wrong item_id raises `DecryptionError` |
| KM-07 | `test_wrap_without_master_key` | Wrap before derive_master_key raises `LocalStorageError` |
| KM-08 | `test_export_import_manifest_roundtrip` | Export manifest, import with same passphrase succeeds |
| KM-09 | `test_import_wrong_passphrase` | Import with wrong passphrase raises `Exception` |
| KM-10 | `test_import_truncated_blob` | Import truncated manifest raises `ManifestError` |
| KM-11 | `test_get_dek_from_manifest` | Retrieve DEK from manifest returns correct key |
| KM-12 | `test_get_dek_missing_item` | Retrieve DEK for nonexistent item raises `ItemNotFoundError` |
| KM-13 | `test_dek_cache` | Cache DEK then retrieve from cache returns same key |
| KM-14 | `test_cache_fifo_eviction` | Cache at max capacity evicts oldest entry (FIFO) |

---

### 3. `test_crypt_storage.py` — Vault Storage (12 tests)

| Test ID | Test Name | What It Proves |
|---------|-----------|----------------|
| VS-01 | `test_save_load_roundtrip` | Save dict then load returns identical dict |
| VS-02 | `test_overwrite_existing` | Save same item_id twice, load returns latest |
| VS-03 | `test_namespace_isolation` | Same item_id in different namespaces are independent |
| VS-04 | `test_invalid_namespace` | Unknown namespace raises `LocalStorageError` |
| VS-05 | `test_load_nonexistent` | Load nonexistent item raises `ItemNotFoundError` |
| VS-06 | `test_delete` | Delete item, list shows empty |
| VS-07 | `test_delete_nonexistent` | Delete nonexistent item raises `ItemNotFoundError` |
| VS-08 | `test_list_items` | List returns sorted item stems |
| VS-09 | `test_list_empty_namespace` | Empty namespace returns `[]` |
| VS-10 | `test_tampered_ciphertext` | Tampered `.enc` file fails on load |
| VS-11 | `test_persistence` | New vault instance on same path can load saved data |
| VS-12 | `test_secure_delete_overwrites` | After delete, `.enc` file no longer exists |

---

### 4. `test_audit.py` — Audit Log (7 tests)

| Test ID | Test Name | What It Proves |
|---------|-----------|----------------|
| AL-01 | `test_append_and_verify` | Append 2 entries, verify chain is intact |
| AL-02 | `test_verify_empty_log` | Empty log verifies as valid |
| AL-03 | `test_tamper_detection` | Mutating an entry field breaks verification |
| AL-04 | `test_persistence` | New AuditLog instance loads previous entries |
| AL-05 | `test_filter_by_namespace` | Filter entries by namespace returns correct subset |
| AL-06 | `test_filter_by_op` | Filter entries by operation type works |
| AL-07 | `test_export_json` | JSON export contains expected compact format |

---

### 5. `test_canary.py` — Canary Detection (15 tests)

| Test ID | Test Name | What It Proves |
|---------|-----------|----------------|
| CA-01 | `test_deploy_creates_files` | Deploy creates canary files on disk |
| CA-02 | `test_check_intact` | Unmodified canaries show zero triggered |
| CA-03 | `test_tamper_detection` | Modified canary is detected by `check_all()` |
| CA-04 | `test_monitor_once_raises` | `monitor_once()` raises `PermissionError` on trigger |
| CA-05 | `test_remove_canaries` | Remove deletes canary files from disk |
| CA-06 | `test_shannon_entropy_random` | Random bytes have entropy > 7.5 |
| CA-07 | `test_shannon_entropy_text` | Repeated byte has entropy == 0.0 |
| CA-08 | `test_check_missing_canary` | Missing canary file is detected as triggered |
| CA-09 | `test_check_all_result_structure` | `check_all()` returns dict with `triggered_count` |
| CA-10 | `test_manifest_hmac_detects_tamper` | Modified manifest fails HMAC verification |
| CA-11 | `test_entropy_threshold_detection` | Low-entropy content triggers alarm |
| CA-12 | `test_deploy_permission_error` | Deploy handles permission errors gracefully |
| CA-13 | `test_monitor_once_returns_result` | `monitor_once()` returns summary dict |
| CA-14 | `test_manifest_hmac_valid` | Unmodified manifest passes HMAC verification |
| CA-15 | `test_high_entropy_not_flagged` | High-entropy random data is not a false positive |

---

### 6. `test_sharing.py` — Multi-User Key Exchange (5 tests)

| Test ID | Test Name | What It Proves |
|---------|-----------|----------------|
| SH-01 | `test_generate_keypair` | Keypair generation returns 16-char ID + 32-byte hex pubkey |
| SH-02 | `test_wrap_unwrap_roundtrip` | Wrap DEK for user, unwrap with matching private key |
| SH-03 | `test_wrong_key_fails` | Unwrap with wrong private key returns `None` |
| SH-04 | `test_share_unshare` | Share then unshare removes user from list |
| SH-05 | `test_try_unlock` | `try_unlock()` with random key returns `None` |

---

### 7. `test_biometric.py` — Biometric Unlock (7 tests)

All biometric tests mock `keyring` and `pylocalauth` — no hardware required.

| Test ID | Test Name | What It Proves |
|---------|-----------|----------------|
| BI-01 | `test_setup_stores_passphrase` | `setup()` calls keyring `set_password` |
| BI-02 | `test_unlock_returns_passphrase` | `unlock()` returns stored passphrase after TTY auth |
| BI-03 | `test_unlock_wrong_passphrase_raises` | Wrong password raises `PermissionError` |
| BI-04 | `test_unlock_no_keyring_raises` | Missing keyring library raises `ConfigError` |
| BI-05 | `test_is_configured_true` | Returns `True` when passphrase is stored |
| BI-06 | `test_is_configured_false` | Returns `False` when no passphrase stored |
| BI-07 | `test_remove_deletes_password` | `remove()` calls keyring `delete_password` |

---

### 8. `test_report.py` — Compliance Reports (10 tests)

| Test ID | Test Name | What It Proves |
|---------|-----------|----------------|
| RP-01 | `test_generate_soc2_valid` | SOC 2 report has controls, summary, valid chain |
| RP-02 | `test_generate_hipaa_valid` | HIPAA report structure is correct |
| RP-03 | `test_generate_gdpr_valid` | GDPR report structure is correct |
| RP-04 | `test_generate_iso27001_valid` | ISO 27001 report structure is correct |
| RP-05 | `test_unknown_framework_raises` | Unknown framework name raises `ConfigError` |
| RP-06 | `test_list_frameworks` | Returns all 4 supported frameworks |
| RP-07 | `test_empty_log_shows_no_data` | Empty audit log -> zero evidence per control |
| RP-08 | `test_tampered_log_chain_invalid` | Tampered audit chain shows `audit_chain_valid: False` |
| RP-09 | `test_export_markdown_format` | Markdown contains headers and control IDs |
| RP-10 | `test_export_json_format` | JSON export is parseable and contains expected keys |

---

### 9. `test_atomic_write.py` — Crash Safety (8 tests)

| Test ID | Test Name | What It Proves |
|---------|-----------|----------------|
| AW-01 | `test_no_temp_files_after_save` | No `.tmp` files remain after single save |
| AW-02 | `test_no_temp_files_after_multiple_saves` | No `.tmp` files after 5 sequential saves |
| AW-03 | `test_no_temp_files_after_delete` | No `.tmp` files after save + delete |
| AW-04 | `test_no_temp_files_after_manifest_write` | No `.tmp` in `keys/` after 2 saves |
| AW-05 | `test_no_temp_files_after_audit_write` | No `.tmp` in `keys/` after 5 audit appends |
| AW-06 | `test_enc_file_exists_with_correct_stem` | Exactly one `.enc` with correct item name exists |
| AW-07 | `test_vault_integrity_after_mixed_ops` | Save -> overwrite -> delete -> save still loads correctly |
| AW-08 | `test_no_temp_files_in_sharing_dir` | No `.tmp` in `keys/` after sharing a vault |

---

### 10. `test_data_leak.py` — No Plaintext on Disk (7 tests)

| Test ID | Test Name | What It Proves |
|---------|-----------|----------------|
| DL-01 | `test_encrypted_item_no_plaintext` | `.enc` file bytes don't contain plaintext values |
| DL-02 | `test_manifest_no_plaintext` | `manifest.enc` doesn't contain secret strings |
| DL-03 | `test_audit_log_no_user_data_content` | Audit log contains only metadata, not user data |
| DL-04 | `test_all_files_encrypted_or_expected_plaintext` | Every vault file is either encrypted or an expected metadata file |
| DL-05 | `test_secure_delete_overwrites_content` | After delete, original ciphertext path no longer exists |
| DL-06 | `test_temp_files_no_plaintext` | No file in vault tree contains secret strings |
| DL-07 | `test_namespace_dirs_not_data` | Directory names are generic labels, not user content |

---

### 11. `test_robustness.py` — Attack, Corruption, Edge Cases (19 tests)

#### Cross-Context Attacks

| Test ID | Test Name | What It Proves |
|---------|-----------|----------------|
| RC-01 | `test_wrong_passphrase_fails_load` | Wrong passphrase raises exception |
| RC-02 | `test_cross_namespace_aad_rejects` | Decrypt with wrong namespace AAD fails |
| RC-03 | `test_cross_item_aad_rejects` | Decrypt with wrong item_id AAD fails |
| RC-04 | `test_tampered_ciphertext_fails_decrypt` | Flipped byte in `.enc` raises exception |
| RC-05 | `test_truncated_ciphertext_fails_decrypt` | Half-length ciphertext raises exception |

#### Corruption Handling

| Test ID | Test Name | What It Proves |
|---------|-----------|----------------|
| RC-06 | `test_corrupted_manifest_raises` | Garbage in `manifest.enc` raises exception |
| RC-07 | `test_missing_manifest_loads_empty` | Deleted manifest -> loads fail gracefully |
| RC-08 | `test_corrupted_audit_log_verify_fails` | Corrupted audit entry -> `verify()` returns False |
| RC-09 | `test_empty_vault_operations` | Empty vault: list returns [], load/delete raise `ItemNotFoundError` |

#### Edge Cases

| Test ID | Test Name | What It Proves |
|---------|-----------|----------------|
| RC-10 | `test_empty_data_save_load` | Save `{}` -> load returns `{}` |
| RC-11 | `test_unicode_data_roundtrip` | Japanese + emoji + accented chars survive roundtrip |
| RC-12 | `test_large_data_roundtrip` | 1MB string value roundtrips correctly |
| RC-13 | `test_special_chars_item_id` | Item IDs with dots, dashes, underscores work |
| RC-14 | `test_double_delete_raises` | Second delete raises `ItemNotFoundError` |
| RC-15 | `test_shared_vault_unlock_wrong_key` | Wrong private key returns `None` from `try_unlock()` |
| RC-16 | `test_audit_log_chain_break` | Modified `op` field breaks chain verification |
| RC-17 | `test_audit_persistence_survives_restart` | New AuditLog instance loads all previous entries |
| RC-18 | `test_invalid_namespace_raises` | Unknown namespace raises `LocalStorageError` |
| RC-19 | `test_overwrite_and_load_latest` | Overwriting an item, new instance loads latest |

---

### 12. `test_cli.py` — CLI Integration (50 tests)

| Test Name | What It Proves |
|-----------|----------------|
| `test_version` | `seal version` outputs correct version string |
| `test_help_shows_all_commands` | `seal --help` lists all expected subcommands |
| `test_init_creates_vault` | `seal init -P <path>` creates valid vault structure |
| `test_init_chacha20` | `seal init --cipher chacha20` creates ChaCha20 vault |
| `test_save_json_data` | `seal save -n ns -i id -d '{}'` succeeds |
| `test_save_from_file` | `seal save -n ns -i id -f file.json` succeeds |
| `test_save_kv_pairs` | `seal save -n ns -i id --kv key=val` works |
| `test_save_at_file` | `@` path prefix for data files |
| `test_save_invalid_namespace` | Invalid namespace raises error |
| `test_load_json_output` | `seal load -n ns -i id -F json` returns JSON |
| `test_load_text_format` | `seal load -n ns -i id -F text` returns text |
| `test_load_missing_item` | Loading nonexistent item returns error |
| `test_list_empty_vault` | `seal list` on empty vault shows none |
| `test_list_with_items` | `seal list` shows saved items |
| `test_list_namespace_filter` | `seal list -n ns` filters correctly |
| `test_list_all_namespaces` | `seal list --all` shows all namespaces |
| `test_list_json_format` | `seal list -F json` returns parseable JSON |
| `test_delete_with_yes_flag` | `seal delete -y` skips confirmation |
| `test_delete_aborts_without_flag` | `seal delete` without `-y` aborts |
| `test_delete_missing_item` | Deleting nonexistent item errors |
| `test_verify_clean` | `seal verify` on clean vault reports CLEAN |
| `test_verify_json_output` | `seal verify -F json` returns valid JSON |
| `test_verify_broken_chain` | `seal verify` on broken chain exits 1 |
| `test_canary_deploy` | `seal canary deploy -n a,b` creates canary files |
| `test_canary_deploy_custom_names` | Custom canary names work |
| `test_canary_check_clean` | `seal canary check` on clean reports 0 triggered |
| `test_canary_check_tampered` | `seal canary check` on tampered exits 1 |
| `test_canary_remove` | `seal canary remove` cleans up |
| `test_report_generate_soc2` | `seal report generate -f soc2` succeeds |
| `test_report_generate_hipaa` | `seal report generate -f hipaa` succeeds |
| `test_report_json_output` | `seal report generate -f soc2 -F json` valid |
| `test_report_markdown_output` | `seal report generate -f soc2 -F markdown` valid |
| `test_report_unknown_framework` | Unknown framework errors |
| `test_share_add` | `seal share add -u <key> -d <dek>` succeeds |
| `test_share_list_empty` | `seal share list` on empty returns none |
| `test_share_list_with_users` | `seal share list` after add shows users |
| `test_share_remove` | `seal share remove -u <id>` succeeds |
| `test_share_invalid_pubkey_length` | Invalid pubkey length errors |
| `test_audit_show_empty` | `seal audit show` on empty vault |
| `test_audit_show_with_entries` | `seal audit show` after operations |
| `test_audit_show_filter_op` | `seal audit show --op save` filters |
| `test_audit_show_filter_ns` | `seal audit show -n personal` filters |
| `test_audit_show_last_n` | `seal audit show --last 3` limits |
| `test_audit_verify_empty` | `seal audit verify` on empty succeeds |
| `test_audit_verify_valid` | `seal audit verify` on clean succeeds |
| `test_audit_verify_broken` | `seal audit verify` on tampered exits 1 |
| `test_audit_export_json` | `seal audit export -F json` works |
| `test_audit_export_markdown` | `seal audit export -F markdown` works |
| `test_audit_export_to_file` | `seal audit export -o file.json` works |
| `test_audit_help` | `seal audit --help` shows subcommands |

---

### 13. `test_file_crypto.py` — File Encryption (9 tests)

| Test Name | What It Proves |
|-----------|----------------|
| `test_file_roundtrip` | Encrypt then decrypt file returns original |
| `test_wrong_passphrase_fails` | Wrong passphrase raises `DecryptionError` |
| `test_tampered_file_fails` | Modified encrypted file raises error |
| `test_bad_magic_fails` | Non-Seal file raises `ValueError` (bad magic) |
| `test_file_not_found` | Missing input file raises `FileNotFoundError` |
| `test_folder_roundtrip` | Encrypt folder then decrypt archive restores contents |
| `test_large_file` | 10MB file roundtrips correctly |
| `test_binary_file` | Binary data (.png bytes) roundtrips correctly |
| `test_not_a_directory` | Encrypt folder on non-directory raises `NotADirectoryError` |

---

### 14. `test_vault_registry.py` — Vault Registry (12 tests)

| Test Name | What It Proves |
|-----------|----------------|
| `test_load_empty` | Registry load on missing file returns `{}` |
| `test_register_and_load` | Register vault then load returns it |
| `test_register_updates_existing` | Re-registering same name updates path |
| `test_unregister` | Unregister removes vault from registry |
| `test_unregister_not_found` | Unregister missing name raises error |
| `test_get_vault_path` | `get_vault_path()` returns correct path |
| `test_get_vault_path_not_found` | Missing vault name raises error |
| `test_touch_vault` | `touch_vault()` adds vault without modifying |
| `test_touch_nonexistent` | Touching nonexistent vault raises error |
| `test_persistence` | New registry instance loads saved data |
| `test_corrupted_file` | Corrupted JSON file raises error |
| `test_multiple_vaults` | Multiple vaults are all stored correctly |

---

### 15. `test_agent.py` — Agent Routing (46 tests)

| Test Name | What It Proves |
|-----------|----------------|
| `test_save_gmail` | "save my gmail password" routes to save |
| `test_save_store` | "store bank pin" routes to save |
| `test_save_add_to_vault` | "add secret to vault" routes to save |
| `test_save_new_entry` | "new entry for wifi" routes to save |
| `test_save_plain` | "save api key" routes to save |
| `test_load_gmail_password` | "get gmail password" routes to load |
| `test_load_show` | "show wifi password" routes to load |
| `test_load_password_for` | "password for email" routes to load |
| `test_load_whats` | "what's my pin" routes to load |
| `test_load_retrieve` | "retrieve api key" routes to load |
| `test_list_passwords` | "list my passwords" routes to list |
| `test_list_entries` | "list all entries" routes to list |
| `test_list_vault` | "what's in my vault" routes to list |
| `test_list_do_i_have` | "do i have a gmail entry" routes to list |
| `test_delete_gmail` | "delete gmail" routes to delete |
| `test_remove_entry` | "remove wifi entry" routes to delete |
| `test_check_integrity` | "check integrity" routes to verify |
| `test_health_check` | "health check" routes to verify |
| `test_is_vault_safe` | "is my vault safe" routes to verify |
| `test_generate_password` | "generate password" routes to generate |
| `test_generate_with_length` | "generate 20 char password" routes to generate with length |
| `test_need_password` | "i need a strong password" routes to generate |
| `test_encrypt_file` | "encrypt file" routes to encrypt |
| `test_decrypt_file` | "decrypt secrets.txt" routes to decrypt |
| `test_check_ransomware` | "check for ransomware" routes to canary check |
| `test_deploy_canaries` | "deploy canaries" routes to canary deploy |
| `test_remove_canaries` | "remove canaries" routes to canary remove |
| `test_show_audit` | "show audit log" routes to audit |
| `test_audit_trail` | "audit trail" routes to audit |
| `test_generate_report` | "generate report" routes to report |
| `test_soc2_report` | "soc2 report" routes to report with framework |
| `test_hipaa_report` | "hipaa report" routes to report with framework |
| `test_list_vaults` | "list vaults" routes to vaults list |
| `test_register_vault` | "register vault" routes to vaults add |
| `test_empty_input` | Empty string returns None |
| `test_unknown_input` | Unrecognized input returns None |
| `test_case_insensitive` | "LIST PASSWORDS" matches case-insensitively |
| `test_confidence_always_one_for_rules` | Rule-based routes have confidence 1.0 |
| `test_to_args_list_save` | RoutedCommand -> args conversion for save |
| `test_to_args_list_list` | RoutedCommand -> args conversion for list |
| `test_to_args_list_clip` | generate command creates --clip flag |
| `test_to_args_list_no_clip` | generate without clipboard no --clip |
| `test_to_args_list_length` | generate with --length N |
| `test_to_args_list_framework` | report with framework -> args |
| `test_to_args_list_empty` | Empty args returns empty list |
| `test_all_patterns_have_groups` | Every regex pattern has a capture group |

---

### 16. `test_tui_screens.py` — TUI Screens (19 tests)

| Test Name | What It Proves |
|-----------|----------------|
| `GeneratorScreen::test_compose` | Screen renders with expected widgets |
| `GeneratorScreen::test_generate_length` | Generator produces correct length password |
| `GeneratorScreen::test_generate_uses_alphabet` | Generated chars are in allowed alphabet |
| `GeneratorScreen::test_strength_label_weak` | Short passwords show "Weak" |
| `GeneratorScreen::test_strength_label_strong` | Long passwords show "Strong" |
| `GeneratorScreen::test_entropy_calculation` | Entropy value is calculated correctly |
| `CanaryScreen::test_import` | Canary screen module loads |
| `CanaryScreen::test_canary_manager_deploy_and_check` | Deploy -> check flow works |
| `CanaryScreen::test_canary_triggered_on_modify` | Modified canary is detected |
| `CanaryScreen::test_canary_remove` | Remove cleans up canary files |
| `ReportScreen::test_import` | Report screen module loads |
| `ReportScreen::test_report_generate` | Report generates successfully |
| `ReportScreen::test_report_markdown_export` | Markdown export works |
| `VaultPickerScreen::test_import` | Picker module loads |
| `VaultPickerScreen::test_registry_roundtrip` | Registry IO works via picker |
| `AppBindings::test_app_import` | App module loads |
| `AppBindings::test_app_has_new_bindings` | App has expected keyboard bindings |
| `AppBindings::test_screen_exports` | All screens are exported from `__init__` |
| `AppBindings::test_tui_exports` | TUI package exports correctly |

---

## Production Integration Tests

**57 tests in `tests/run_production.py`.** Run directly (not pytest):

```bash
python tests/run_production.py
```

These tests invoke the CLI as a real user would, using `subprocess.run()`:

| Test | What It Proves |
|------|----------------|
| `help` | `seal --help` prints usage |
| `invoke without subcommand` | `seal` with no args lists vaults + hint |
| `init creates vault` | Vault directory structure created on disk |
| `init with existing vault` | Re-init on existing vault succeeds |
| `init --json returns JSON` | JSON output valid parseable |
| `init --json errors when no passphrase` | Missing passphrase in JSON mode fails fast |
| `save and load with namespace` | Full roundtrip through real CLI |
| `load missing item errors` | Load nonexistent item returns error |
| `list items` | List shows saved items |
| `list --format json` | JSON list output is parseable |
| `delete item` | Delete then verify removal |
| `verify vault` | Verify on clean vault reports OK |
| `wrong passphrase fails` | Wrong passphrase on load errors |
| `file encrypt/decrypt roundtrip` | Full file encrypt then decrypt |
| `file encrypt --json` | JSON output from encrypt |
| `file decrypt --json` | JSON output from decrypt |
| `decrypt bogus file errors` | Random file fails decrypt |
| `decrypt pre-checks output exists` | Decrypt checks output path before work |
| `vaults list` | Registry list shows vaults |
| `vaults list --json` | JSON vault list is parseable |
| `doctor` | Doctor reports vault health |
| `doctor --json` | JSON doctor output |
| `doctor on vault` | Doctor on specific vault |
| `generate password` | Generate creates password |
| `generate with length` | Password respects length parameter |
| `generate invalid length rejected` | Out-of-range length errors |
| `keygen` | Key generation succeeds |
| `canary deploy and check` | Canary lifecycle through CLI |
| `report generate` | Report generation via CLI |
| `audit show` | Audit log display via CLI |
| `ask command` | Agent routing via CLI |
| `agent list my items` | Agent list pattern works |
| `SEAL_PASSPHRASE env var` | Env var passphrase works |
| `Unicode safety` | Unicode characters in paths/content work |
| `binary value roundtrip` | Binary data survives CLI roundtrip |
| `unknown command errors` | Unknown subcommand exits with error |
| `--help for all commands` | Every command has --help |
| `empty vault report` | Empty vault generates valid report |
| `agent save/load roundtrip` | Agent routes save then load |
| `canary alerts on tamper` | Modified canary triggers alert |
| `verify detects tampered audit log` | Broken audit chain detected |
| `empty vault list` | Empty vault lists nothing |
| `full audit lifecycle` | Complete audit flow end-to-end |
| `non-TTY no hang` | Non-interactive mode doesn't hang |
| `generate boundary lengths` | Min/max length passwords work |
| `mixed items` | Multiple items across namespaces |
| `delete nonexistent item errors` | Deleting missing item errors |
| `keygen creates keypair` | Keypair files created on disk |
| `agent asks respond` | Agent `-x` execute flag works |
| `special characters in values` | Special chars survive CLI roundtrip |
| `long value store/load` | Large data through CLI |
| `version command` | Version output correct |
| `biometric --help` | Biometric command has help |
| `share --help` | Share command has help |
| `init with cipher chacha20` | ChaCha20 vault via CLI |
| `encrypt with empty file` | Empty file encrypts/decrypts |
| `doctor on non-existent vault` | Doctor on missing vault errors gracefully |

---

## Test Coverage by Module

| Module | Source LOC | Tests | Coverage Scope |
|--------|-----------|-------|----------------|
| `cipher.py` | 134 | 12 | Full: encrypt/decrypt, AEAD, key sizes, both suites |
| `key_manager.py` | 200 | 14 | Full: derivation, wrap/unwrap, manifest, cache |
| `crypt_storage.py` | 166 | 19 | Full: save/load/delete/list, persistence, atomic, data leak |
| `audit.py` | 133 | 7 | Full: append, verify, tamper, persistence, filter, export |
| `canary.py` | 180 | 15 | Full: deploy, check, tamper, monitor, remove, entropy, HMAC |
| `sharing.py` | 154 | 5 | Core: keypair, wrap/unwrap, share/unshare, unlock |
| `biometric.py` | 113 | 7 | Full: setup, unlock, configured, remove (mocked) |
| `report.py` | 236 | 10 | Full: all 4 frameworks, export, empty/tampered log |
| `file_crypto.py` | 120 | 9 | Full: file roundtrip, folder, large/binary, errors |
| `vault_registry.py` | 109 | 12 | Full: register, unregister, touch, persistence, corruption |
| `agent.py` | 256 | 46 | Full: all route patterns, edge cases, args conversion |
| `cli.py` | 1579 | 50 | Full: all 28 commands, flags, JSON output, error paths |
| `tui/` | ~1200 | 19 | Core screens: generator, canary, report, picker, bindings |
| `_errors.py` | 78 | — | Covered indirectly via exception assertions |

---

## Test Patterns Used

### Fixtures

```python
@pytest.fixture
def vault_path(self):
    path = tempfile.mkdtemp(prefix="seal_test_")
    yield path
    shutil.rmtree(path, ignore_errors=True)

@pytest.fixture
def vault(self, vault_path):
    return AegisVault(vault_path, "test-passphrase")
```

### Exception Testing

```python
with pytest.raises(DecryptionError):
    cipher.decrypt_combined(wrong_key, blob, aad)
```

### Mocking (biometric tests)

```python
with patch.dict("sys.modules", {
    "keyring": mock_keyring,
    "pylocalauth": MagicMock(),
}):
    bio = BiometricUnlock(vault_id="test")
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'aegis.xxx'`

Run `pip install -e .` from the project root. Re-install after adding new source files.

### `No module named pytest`

```bash
python -m pip install pytest
```

### Tests pass individually but fail in batch

Some tests use shared temp directories. Run with `--forked` or ensure each test class has its own `vault_path` fixture.

### `PermissionError` in biometric tests

Biometric module requires `keyring` and optionally `pylocalauth`. Tests mock these — do not install real versions in the test environment.

---

## Adding New Tests

1. Create `tests/test_<module>.py`
2. Import from `aegis.<module>`
3. Use the `vault_path` / `vault` fixture pattern
4. Run `python -m pytest tests/ -v` to verify
5. Update this file with the new test index
