from __future__ import annotations

import hashlib
import os
import tarfile
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from aegis.cipher import AeadCipher, CipherConfig

_KDF_INFO = b"seal-file-encrypt-v1"
_SALT_LEN = 32
_MAGIC = b"SEAL"  # 4-byte magic prefix


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=_KDF_INFO,
    ).derive(passphrase.encode("utf-8"))


def _resolve_output(input_path: Path, output_path: Path, for_encrypt: bool) -> Path:
    if not output_path.is_dir():
        return output_path
    name = input_path.name if for_encrypt else input_path.stem
    return output_path / name


def encrypt_file(input_path: str | Path, output_path: str | Path,
                  passphrase: str) -> None:
    """Encrypt a single file. Output = MAGIC + salt + (nonce + ciphertext + tag)."""
    src = Path(input_path)
    if not src.exists():
        raise FileNotFoundError(f"File not found: {src}")

    data = src.read_bytes()
    salt = os.urandom(_SALT_LEN)
    key = _derive_key(passphrase, salt)
    cipher = AeadCipher()
    encrypted = cipher.encrypt_combined(key, data)

    dst = _resolve_output(src, Path(output_path), for_encrypt=True)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        f.write(_MAGIC)
        f.write(salt)
        f.write(encrypted)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, dst)


def decrypt_file(input_path: str | Path, output_path: str | Path,
                  passphrase: str) -> None:
    """Decrypt a file produced by encrypt_file."""
    src = Path(input_path)
    if not src.exists():
        raise FileNotFoundError(f"File not found: {src}")

    raw = src.read_bytes()
    if raw[:4] != _MAGIC:
        raise ValueError("Not a Seal-encrypted file (bad magic header)")

    salt = raw[4:4 + _SALT_LEN]
    encrypted = raw[4 + _SALT_LEN:]

    key = _derive_key(passphrase, salt)
    cipher = AeadCipher()
    plaintext = cipher.decrypt_combined(key, encrypted)

    dst = _resolve_output(src, Path(output_path), for_encrypt=False)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        f.write(plaintext)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, dst)


def encrypt_folder(folder_path: str | Path, output_path: str | Path,
                    passphrase: str) -> None:
    """Tar a folder, then encrypt the archive."""
    src = Path(folder_path)
    if not src.is_dir():
        raise NotADirectoryError(f"Not a directory: {src}")

    dst = Path(output_path)
    if dst.is_dir():
        dst = dst / (src.name + ".tar.seal")

    with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        with tarfile.open(tmp_path, "w") as tar:
            tar.add(str(src), arcname=src.name)
        encrypt_file(tmp_path, str(dst), passphrase)
    finally:
        os.unlink(tmp_path)


def decrypt_archive(archive_path: str | Path, output_dir: str | Path,
                     passphrase: str) -> None:
    """Decrypt an archive produced by encrypt_folder, then extract."""
    dst = Path(output_dir)
    dst.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        decrypt_file(archive_path, tmp_path, passphrase)
        with tarfile.open(tmp_path, "r") as tar:
            tar.extractall(path=str(dst))
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
