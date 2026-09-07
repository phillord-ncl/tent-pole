from tent_pole import file as tp_file


class FakeCanvasFile:
    def __init__(self, filename, size=100, content=b"file content",
                 uuid="uuid-1", id=1, media_entry_id=None):
        self.filename = filename
        self.size = size
        self._content = content
        self.uuid = uuid
        self.id = id
        self.media_entry_id = media_entry_id
        self.__dict__["content-type"] = "text/plain"

    def get_contents(self, binary=False):
        return self._content if binary else self._content.decode()


class FakeCourseForFile:
    def __init__(self, files):
        self.id = 999
        self._files = files

    def get_files(self):
        return self._files


def write_local_file(path, content=b"file content"):
    path.write_bytes(content)
    return str(path)


def test_data_includes_hash_and_size(tmp_path):
    local = write_local_file(tmp_path / "example.txt")
    canvas_file = FakeCanvasFile("example.txt", size=len(b"file content"))
    fake_course = FakeCourseForFile([canvas_file])

    data = tp_file.__data(local, fake_course)

    assert data["hash"] == tp_file.manifest.hash_file(local)
    assert data["size"] == len(b"file content")


def test_local_drift_none_when_unchanged(tmp_path):
    local = write_local_file(tmp_path / "example.txt")
    recorded = {"hash": tp_file.manifest.hash_file(local)}

    assert tp_file.__local_drift(local, recorded) is None


def test_local_drift_detects_changed_file(tmp_path):
    path = tmp_path / "example.txt"
    local = write_local_file(path, b"original")
    recorded = {"hash": tp_file.manifest.hash_file(local)}

    write_local_file(path, b"edited")

    assert tp_file.__local_drift(local, recorded) is not None


def test_local_drift_flags_missing_recorded_hash(tmp_path):
    local = write_local_file(tmp_path / "example.txt")

    assert tp_file.__local_drift(local, {}) is not None


def test_remote_drift_none_when_size_matches(tmp_path):
    local = write_local_file(tmp_path / "example.txt")
    canvas_file = FakeCanvasFile("example.txt", size=100)
    fake_course = FakeCourseForFile([canvas_file])
    recorded = {"size": 100}

    assert tp_file.__remote_drift(local, recorded, fake_course) is None


def test_remote_drift_detects_size_change(tmp_path):
    local = write_local_file(tmp_path / "example.txt")
    canvas_file = FakeCanvasFile("example.txt", size=999)
    fake_course = FakeCourseForFile([canvas_file])
    recorded = {"size": 100}

    assert tp_file.__remote_drift(local, recorded, fake_course) is not None


def test_remote_drift_file_missing_on_canvas(tmp_path):
    local = write_local_file(tmp_path / "example.txt")
    fake_course = FakeCourseForFile([])  # nothing uploaded with this name
    recorded = {"size": 100}

    assert tp_file.__remote_drift(local, recorded, fake_course) is not None


def test_remote_drift_deep_passes_when_content_matches(tmp_path):
    local = write_local_file(tmp_path / "example.txt", b"same bytes")
    canvas_file = FakeCanvasFile("example.txt", size=10, content=b"same bytes")
    fake_course = FakeCourseForFile([canvas_file])
    recorded = {"size": 10, "hash": tp_file.manifest.hash_file(local)}

    assert tp_file.__remote_drift(local, recorded, fake_course, deep=True) is None


def test_remote_drift_deep_detects_content_mismatch(tmp_path):
    local = write_local_file(tmp_path / "example.txt", b"local bytes")
    canvas_file = FakeCanvasFile("example.txt", size=11, content=b"other bytes")
    fake_course = FakeCourseForFile([canvas_file])
    recorded = {"size": 11, "hash": tp_file.manifest.hash_file(local)}

    assert tp_file.__remote_drift(local, recorded, fake_course, deep=True) is not None


def test_remote_drift_not_deep_ignores_content_mismatch_if_size_matches(tmp_path):
    """--deep is opt-in: without it, a size-only match should pass even
    if content secretly differs (that's the whole cheap/thorough tradeoff)."""
    local = write_local_file(tmp_path / "example.txt", b"local bytes")
    canvas_file = FakeCanvasFile("example.txt", size=11, content=b"remote diff")
    fake_course = FakeCourseForFile([canvas_file])
    recorded = {"size": 11, "hash": tp_file.manifest.hash_file(local)}

    assert tp_file.__remote_drift(local, recorded, fake_course, deep=False) is None
