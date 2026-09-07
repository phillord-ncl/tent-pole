import hashlib


def hash_file(path):
    """SHA-256 hex digest of a local file's bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_bytes(data):
    """SHA-256 hex digest of raw bytes (e.g. downloaded remote content)."""
    return hashlib.sha256(data).hexdigest()
