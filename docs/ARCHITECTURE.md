# Architecture: Seal (Aegis Vault)

## 15-Module System

```
┌─────────────────────────────────────────────────────────────────────┐
│                            cli.py                                   │
│                  Click + Rich CLI (28 commands)                     │
├─────────────────────────────────────────────────────────────────────┤
│                        tui/app.py                                   │
│              Textual TUI (8 screens, vault picker)                  │
├─────────────┬─────────────┬─────────────┬───────────────────────────┤
│  crypt_     │    audit    │   canary    │         sharing           │
│  storage.py │    .py      │    .py      │           .py             │
│  AegisVault │  SHA-256    │  Decoy      │  X25519 stanzas           │
│  save/load  │  chain log  │  detection  │  multi-user DEK           │
├─────────────┼─────────────┼─────────────┼───────────────────────────┤
│  file_      │   report    │  biometric  │    vault_registry.py      │
│  crypto.py  │    .py      │    .py      │  ~/.seal/vaults.json      │
│  standalone │  SOC2/      │  Windows    │  central vault index      │
│  encrypt    │  HIPAA/     │  Hello +    │                           │
│             │  GDPR/ISO   │  keyring    │                           │
├─────────────┴─────────────┴─────────────┴───────────────────────────┤
│                          agent.py                                   │
│             SmolLM2-135M-Instruct + rule-based fallback             │
├─────────────────────────────────────────────────────────────────────┤
│                       key_manager.py                                │
│           PBKDF2 (600K) → DEK wrap/unwrap → manifest                │
├─────────────────────────────────────────────────────────────────────┤
│                         cipher.py                                   │
│            AES-256-GCM / ChaCha20-Poly1305 AEAD                     │
├─────────────────────────────────────────────────────────────────────┤
│                        _errors.py                                   │
│               9 custom exception classes                            │
└─────────────────────────────────────────────────────────────────────┘
```

## Layer Stack

```
┌──────────────────────────────────────────────────┐
│              LocalEncryptedStorage                │
│  ┌─────────────┬──────────────┬───────────────┐  │
│  │  save()     │  load()      │  delete()     │  │
│  │  list()     │              │               │  │
│  └──────┬──────┴──────┬───────┴───────┬───────┘  │
│         │             │               │           │
│  ┌──────▼─────────────▼───────────────▼───────┐  │
│  │           KeyManager                        │  │
│  │  ┌─────────────┬────────────────────────┐  │  │
│  │  │ derive_master_key()                   │  │  │
│  │  │ generate_dek() / wrap_dek()           │  │  │
│  │  │ unwrap_dek() / get_dek()             │  │  │
│  │  │ export/import_encrypted_manifest()    │  │  │
│  │  └─────────────┬────────────────────────┘  │  │
│  │                │                            │  │
│  │  ┌─────────────▼────────────────────────┐  │  │
│  │  │           AeadCipher                  │  │  │
│  │  │  encrypt() / decrypt()               │  │  │
│  │  │  encrypt_combined() / decrypt_combined│  │  │
│  │  └──────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

## Data Flow: save()

```
1. Validate namespace (non-empty, no / or \ characters)
2. Validate item_id (no /, \, or .. sequences)
3. Check if item_id already has a DEK
   ├─ YES → reuse existing DEK
   └─ NO  → generate new DEK → wrap under Master Key → add to manifest
4. JSON-serialize the data dict
5. Construct AAD = b"aegis_ns:" + b"namespace:item_id"
6. Encrypt(serialized_data, dek, aad) → blob
7. Atomic write: .tmp → flush → fsync → os.replace
8. If manifest changed → save manifest (same atomic pattern)
```

## Data Flow: load()

```
1. Validate namespace and item_id
2. Read .enc file from disk
3. Look up DEK via KeyManager (cache → manifest → unwrap)
4. Construct AAD = b"aegis_ns:" + b"namespace:item_id"
5. Decrypt(blob, dek, aad) → serialized_data
6. JSON-deserialize → return dict
```

## On-Disk Layout

```
vault/
├── keys/
│   ├── manifest.enc          # salt(16) || encrypted(JSON{items: {id: {dek, ns, created}}})
│   ├── audit.log             # NDJSON: {seq, ts, op, namespace, item_id, prev_hash, hash}
│   └── stanzas.json          # X25519 wrapped DEKs for shared users
├── personal/                 # any namespace name
│   ├── doc1.enc              # nonce(12) || ciphertext || tag(16)
│   └── doc2.enc
├── banking/
│   └── chase.enc
├── work/
│   └── api-config.enc
└── .canaries/
    ├── canaries.json         # {name, path, original_hash, original_entropy}
    ├── canaries.json.hmac    # HMAC-SHA256 signature
    ├── passwords.xlsx        # Decoy file (512 bytes random)
    ├── financials.pdf        # Decoy file
    └── wallet.dat            # Decoy file
```

## Blob Format

```
┌──────────┬────────────────────┬──────────┐
│ nonce    │ ciphertext         │ auth_tag │
│ (12 B)   │ (len(data) B)      │ (16 B)   │
└──────────┴────────────────────┴──────────┘
```

## Manifest Format

```
┌──────┬─────────────────────────────────────┐
│ salt │ encrypted JSON payload              │
│(16B) │ nonce(12) || ct || tag(16)          │
└──────┴─────────────────────────────────────┘
```

## File Encryption Format (standalone)

```
┌──────┬──────────┬────────────────────┬──────────┐
│ SEAL │ salt(32) │ nonce(12)          │ ct || tag│
│magic │          │                    │          │
└──────┴──────────┴────────────────────┴──────────┘
```

## AAD Domain Separation

| Context | AAD Value |
|---------|-----------|
| DEK wrapping | `b"aegis_dek_wrap_v1" + item_id_bytes` |
| Manifest encryption | `b"aegis_manifest_v1"` |
| File encryption | `b"aegis_ns:" + b"namespace:item_id"` |

Different AAD values for different purposes prevent ciphertext relocation attacks.

## Modules

| Module | LOC | Role |
|--------|-----|------|
| `cipher.py` | 104 | AEAD encrypt/decrypt (AES-GCM, ChaCha20) |
| `key_manager.py` | 162 | PBKDF2 derivation, DEK wrap/unwrap, manifest I/O |
| `crypt_storage.py` | 168 | Vault facade: save/load/delete/list, atomic writes |
| `_errors.py` | 58 | 9 custom exception classes |
| `audit.py` | 121 | SHA-256 chained append-only audit log |
| `canary.py` | 210 | Ransomware canary decoy detection + HMAC manifest |
| `sharing.py` | 137 | X25519 key exchange for multi-user access |
| `biometric.py` | 146 | Windows Hello fingerprint + keyring integration |
| `report.py` | 225 | SOC 2 / HIPAA / GDPR / ISO 27001 report generation |
| `file_crypto.py` | 98 | Standalone file/folder encryption (no vault required) |
| `vault_registry.py` | 66 | Central vault registry (`%LOCALAPPDATA%/Seal/vaults.json`) |
| `agent.py` | 246 | SmolLM2-135M-Instruct + rule-based NL routing |
| `cli.py` | 1,344 | Click + Rich CLI (28 commands) |
| `tui/app.py` | 154 | Textual app shell, screen routing |
| `tui/screens/*.py` | 1,609 | 10 screens |
| **Total** | **4,848** | |

## TUI Screens

| Screen | File | Role |
|--------|------|------|
| VaultPickerScreen | `picker.py` | Registry-based vault selection |
| LoginScreen | `login.py` | Passphrase entry + biometric |
| VaultScreen | `vault.py` | Browse entries, search, edit, delete |
| NewItemScreen | `vault.py` | Create entry with free-form namespace |
| EntryScreen | `vault.py` | Edit raw JSON of existing entry |
| GeneratorScreen | `generator.py` | Password generator with strength meter |
| CanaryScreen | `canary.py` | Deploy/check/remove canary files |
| ReportScreen | `report.py` | Compliance report generation |
| FileCryptoScreen | `file_crypto.py` | Standalone file encrypt/decrypt |
| FileBrowserScreen | `file_browser.py` | File/directory picker for encrypt paths |
| HelpScreen | `help_screen.py` | Keyboard shortcuts + CLI examples |
| CreateVaultScreen | `create_vault.py` | In-app vault creation |

## Test Suite

309 tests — 252 unit (16 files) + 57 production integration. See [TEST_DOCUMENTATION.md](TEST_DOCUMENTATION.md) for the full indexed test catalog.

```bash
python -m pytest tests/ -v                # Run all 252 unit tests
python tests/run_production.py            # Run 57 production tests
python -m pytest tests/test_cipher.py -v  # Run one module
```
