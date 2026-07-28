import os
import tempfile
from pathlib import Path

import pytest

from aegis.file_crypto import encrypt_file, decrypt_file, encrypt_folder, decrypt_archive


PASSPHRASE = "test-passphrase-123"


class TestFileCrypto:
    def test_file_roundtrip(self, tmp_path):
        src = tmp_path / "secret.txt"
        enc = tmp_path / "secret.enc"
        dec = tmp_path / "secret.dec"
        src.write_text("hello world")

        encrypt_file(src, enc, PASSPHRASE)
        assert enc.exists()
        assert enc.read_bytes()[:4] == b"SEAL"

        decrypt_file(enc, dec, PASSPHRASE)
        assert dec.read_text() == "hello world"

    def test_wrong_passphrase_fails(self, tmp_path):
        src = tmp_path / "secret.txt"
        enc = tmp_path / "secret.enc"
        dec = tmp_path / "secret.dec"
        src.write_text("hello world")
        encrypt_file(src, enc, PASSPHRASE)

        with pytest.raises(Exception):
            decrypt_file(enc, dec, "wrong-password")

    def test_tampered_file_fails(self, tmp_path):
        src = tmp_path / "secret.txt"
        enc = tmp_path / "secret.enc"
        dec = tmp_path / "secret.dec"
        src.write_bytes(os.urandom(512))
        encrypt_file(src, enc, PASSPHRASE)

        raw = bytearray(enc.read_bytes())
        raw[-1] ^= 0xFF
        enc.write_bytes(bytes(raw))

        with pytest.raises(Exception):
            decrypt_file(enc, dec, PASSPHRASE)

    def test_bad_magic_fails(self, tmp_path):
        enc = tmp_path / "fake.enc"
        dec = tmp_path / "fake.dec"
        enc.write_bytes(b"FAKE" + os.urandom(100))

        with pytest.raises(ValueError, match="bad magic"):
            decrypt_file(enc, dec, PASSPHRASE)

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            encrypt_file(tmp_path / "nope.txt", tmp_path / "out.enc", PASSPHRASE)

    def test_folder_roundtrip(self, tmp_path):
        folder = tmp_path / "mydata"
        folder.mkdir()
        (folder / "a.txt").write_text("alpha")
        (folder / "b.txt").write_text("beta")
        sub = folder / "sub"
        sub.mkdir()
        (sub / "c.txt").write_text("gamma")

        enc = tmp_path / "mydata.enc"
        out = tmp_path / "restored"
        encrypt_folder(folder, enc, PASSPHRASE)
        assert enc.exists()

        decrypt_archive(enc, out, PASSPHRASE)
        assert (out / "mydata" / "a.txt").read_text() == "alpha"
        assert (out / "mydata" / "b.txt").read_text() == "beta"
        assert (out / "mydata" / "sub" / "c.txt").read_text() == "gamma"

    def test_large_file(self, tmp_path):
        src = tmp_path / "large.bin"
        enc = tmp_path / "large.enc"
        dec = tmp_path / "large.dec"
        data = os.urandom(1024 * 1024)
        src.write_bytes(data)

        encrypt_file(src, enc, PASSPHRASE)
        decrypt_file(enc, dec, PASSPHRASE)
        assert dec.read_bytes() == data

    def test_binary_file(self, tmp_path):
        src = tmp_path / "image.png"
        enc = tmp_path / "image.enc"
        dec = tmp_path / "image.dec"
        data = os.urandom(256)
        src.write_bytes(data)

        encrypt_file(src, enc, PASSPHRASE)
        decrypt_file(enc, dec, PASSPHRASE)
        assert dec.read_bytes() == data

    def test_not_a_directory(self, tmp_path):
        src = tmp_path / "file.txt"
        src.write_text("not a dir")
        with pytest.raises(NotADirectoryError):
            encrypt_folder(src, tmp_path / "out.enc", PASSPHRASE)
