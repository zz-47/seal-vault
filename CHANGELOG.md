# Changelog

All notable changes to Seal will be documented in this file.

## [0.3.0] - 2026-07-29

### Changed
- Default vault path moved to `%LOCALAPPDATA%\Seal\vaults\` (was relative to CWD)
- Registry moved to `%LOCALAPPDATA%\Seal\vaults.json` (was `~/.seal/vaults.json`)
- CLI defaults to registry path instead of `Path.cwd()` when `--path` omitted
- `seal init --path` now optional (defaults to `%LOCALAPPDATA%\Seal\vaults\my-vault`)
- `seal` with no arguments lists registered vaults + help hint
- Empty vault compliance status uses `relevant` flags only (ignores chain_valid)
- File browser starts on `Desktop` not `Documents` (Documents has broken Windows junctions)
- File browser DataTable uses `cursor_type="row"` (was `"cell"`, was not firing `RowSelected`)
- `seal encrypt/decrypt` output path accepts directories — auto-derives filename from input

### Added
- `--json` flag to `seal encrypt/decrypt/init/doctor/vaults list` for machine-readable output
- File encrypt/decrypt TUI screen (Ctrl+T) — standalone or vault passphrase
- File browser screen for selecting files/folders in encrypt/decrypt TUI
- Help screen (Ctrl+H) with keyboard shortcut reference + CLI examples
- Help button on vault screen and picker toolbar
- Auto-scan `%LOCALAPPDATA%\Seal\vaults\` for existing vaults on picker load
- `_default_vault_dir()` and `touch_vault()` in vault_registry
- 57 production integration tests (CLI as real user would invoke it)

### Fixed
- Biometric unlock callback never called after successful Windows Hello auth
- `_get_seal_dir()` crashes on Linux when `LOCALAPPDATA` env var is unset
- `ManifestError` duplicate definition in `_errors.py`
- `AuditIntegrityError` missing from `_errors.py` `__all__`
- Double PBKDF2 on vault open (`derive_master_key` called before `if not exists` check)
- `_pop_or_exit` leaves blank terminal when no screens remain on VaultPickerScreen
- Null guard crashes in `vault.py` (6 sites) and `canary.py` (3 sites)
- Missing `logger` in `canary.py` — `NameError` on deploy failure
- CWD fallback in TUI app, allowing silent misoperation
- File browser crashes on Windows junctions — catch all `OSError` in `_populate()`
- Decrypt error paths use `sys.exit(1)` (was `return` 0)
- Canary check uses `sys.exit(1)` when triggered or no canaries deployed
- Verify uses `sys.exit(1)` when audit chain broken or canary triggered
- `rich.markup.escape()` on generated passwords prevents `MarkupError` on `[/`
- `encrypt_file`/`decrypt_file` — `dst.with_suffix(".tmp")` mangles directory paths (e.g. `Admin` → `Admin.tmp`)
- `Missing Label import in help_screen.py`

## [0.2.0] - 2026-07-28

### Added
- **Vault registry** — `seal vaults list/add/remove` manages multiple vaults in `~/.seal/vaults.json`
- **File encryption** — `seal encrypt/decrypt` for standalone file and folder encryption (no vault required)
- **Free-form namespaces** — any string label (not restricted to personal/work/archive)
- **Natural language agent** — `seal ask "..."` routes NL commands via SmolLM2-135M-Instruct or rule-based fallback
- **TUI vault picker** — registry-based vault selection before login (no filesystem scan)
- **TUI new entry** — free-form namespace input (replaces dropdown)
- **CLI vault commands** — `seal vaults list`, `seal vaults add -n name -P path`, `seal vaults remove -n name`
- **CLI encrypt/decrypt** — `seal encrypt -i file -o file.enc`, `seal decrypt -i file.enc -o file`
- **CLI ask command** — `seal ask "natural language"` with `-x` flag to execute routed command
- **Agent test suite** — 46 tests covering all route patterns and edge cases

### Fixed
- **Path traversal** — `item_id` now rejects `/`, `\`, and `..` sequences
- **Timing attack on biometric** — `pw == stored` replaced with `hmac.compare_digest()`
- **Biometric hint** — incorrect `seal vault-setup` command fixed to `seal biometric enroll`
- **Canary bare except** — `except:` replaced with `except Exception:` (no longer catches KeyboardInterrupt)
- **CLI tamper error** — `_get_vault` now handles AuditLog/CanaryManager init failures gracefully
- **CLI version** — `version_option` package name corrected from `aegis-vault` to `seal`
- **CLI init message** — removed hardcoded "personal, work, archive" namespace list
- **CLI list** — `keys/` directory no longer appears as a namespace in output
- **TUI list** — `keys/` directory no longer leaks into vault browser as a namespace
- **TUI CSS** — fixed dead `#ns-select` selector (widget is `#ns-input`)
- **TUI canary** — replaced fragile `hasattr` check with `getattr` pattern
- **Agent canary regex** — `canaries?` fixed to `canar(?:y|ies)` (matches singular "canary")
- **Agent pattern order** — canary patterns moved before delete to prevent false matches
- **Agent duplicate patterns** — removed duplicate list patterns
- **Agent model** — switched from base SmolLM2-135M to SmolLM2-135M-Instruct
- **Agent prompt** — now uses ChatML template via `apply_chat_template`
- **Agent JSON parsing** — regex extraction replaces fragile `split("->")` parsing
- **Agent token decoding** — only new tokens decoded (excludes prompt from output)

### Changed
- Namespaces are now free-form strings (validation: non-empty, no `/` or `\`)
- TUI flow changed: vault picker → login (was: login → vault picker)
- Agent execution order: model first, rule-based fallback (was: rules first, model second)

## [0.1.0] - 2026-07-17

### Added
- Three-layer envelope encryption (cipher → key_manager → crypt_storage)
- AES-256-GCM and ChaCha20-Poly1305 dual-algorithm support
- PBKDF2-HMAC-SHA256 key derivation (600K iterations)
- Per-file Data Encryption Keys (DEKs) wrapped under Master Key
- Encrypted manifest with AAD domain separation
- Namespace-routed storage (personal, work, archive)
- Atomic writes (tmp → fsync → replace)
- Secure deletion (random overwrite before unlink)
- AAD-bound tamper detection
- FIFO DEK cache (128 entries)
- CLI interface (init, store, retrieve, list, delete)
- Benchmark suite (AES-GCM vs ChaCha20 throughput)
- Docker support
- 73 test cases
