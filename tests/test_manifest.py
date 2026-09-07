import hashlib

from tent_pole import manifest


def test_hash_file_matches_known_sha256(tmp_path):
    f = tmp_path / "a.txt"
    f.write_bytes(b"hello world")

    assert manifest.hash_file(str(f)) == hashlib.sha256(b"hello world").hexdigest()


def test_hash_file_changes_when_content_changes(tmp_path):
    f = tmp_path / "a.txt"
    f.write_bytes(b"version one")
    first = manifest.hash_file(str(f))

    f.write_bytes(b"version two")
    second = manifest.hash_file(str(f))

    assert first != second


def test_hash_bytes_matches_known_sha256():
    assert manifest.hash_bytes(b"hello world") == hashlib.sha256(b"hello world").hexdigest()


def test_hash_file_and_hash_bytes_agree_on_same_content(tmp_path):
    f = tmp_path / "a.txt"
    f.write_bytes(b"same content")

    assert manifest.hash_file(str(f)) == manifest.hash_bytes(b"same content")
