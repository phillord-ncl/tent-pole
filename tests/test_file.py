import toml
from click.testing import CliRunner

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
        self.upload_calls = []

    def get_files(self):
        return self._files

    def upload(self, filename, **kwargs):
        self.upload_calls.append((filename, kwargs))
        return True, {}


class SlowlyResolvingCourse:
    """A course whose one file's media_entry_id starts as "maybe" (as
    Canvas returns right after a video upload, before it decides
    whether to transcode) and resolves to a real id after a couple of
    get_files() calls -- mimicking the real polling scenario --wait
    exists for."""
    def __init__(self, filename, resolves_after=2):
        self.id = 999
        self.filename = filename
        self.calls = 0
        self.resolves_after = resolves_after

    def get_files(self):
        self.calls += 1
        media_entry_id = "maybe" if self.calls <= self.resolves_after else "m-real-id"
        return [FakeCanvasFile(self.filename, media_entry_id=media_entry_id)]


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


def test_push_uploads_into_the_tent_pole_folder(tmp_path, monkeypatch):
    """The whole point of this feature: every push lands in a dedicated
    folder (fixed name, default-on -- not opt-in), so "did tent-pole
    manage this" becomes a cheap folder check later, instead of
    landing in Canvas's generic "unfiled" folder like everything else."""
    local = write_local_file(tmp_path / "example.txt")
    fake_course = FakeCourseForFile([])
    monkeypatch.setattr(tp_file.course, "course_obj", lambda: fake_course)

    runner = CliRunner()
    result = runner.invoke(tp_file.file, ["push", local])

    assert result.exit_code == 0, result.output
    assert len(fake_course.upload_calls) == 1
    uploaded_filename, kwargs = fake_course.upload_calls[0]
    assert uploaded_filename == local
    assert kwargs == {"parent_folder_path": tp_file.TENT_POLE_FOLDER}
    assert tp_file.TENT_POLE_FOLDER == "tent-pole"


def test_dump_without_wait_does_not_poll(tmp_path, monkeypatch):
    """--wait is opt-in: a plain dump writes immediately even if
    media_entry_id is still "maybe", same as before this feature."""
    local = write_local_file(tmp_path / "video.mp4")
    canvas_file = FakeCanvasFile("video.mp4", media_entry_id="maybe")
    fake_course = FakeCourseForFile([canvas_file])
    monkeypatch.setattr(tp_file.course, "course_obj", lambda: fake_course)

    runner = CliRunner()
    result = runner.invoke(tp_file.file, ["dump", local])

    assert result.exit_code == 0, result.output
    with open(local + ".tpf") as fh:
        recorded = toml.load(fh)
    assert recorded["media_entry_id"] == "maybe"


def test_dump_wait_polls_until_media_entry_id_resolves(tmp_path, monkeypatch):
    local = write_local_file(tmp_path / "video.mp4")
    fake_course = SlowlyResolvingCourse("video.mp4", resolves_after=2)
    monkeypatch.setattr(tp_file.course, "course_obj", lambda: fake_course)
    monkeypatch.setattr(tp_file.time, "sleep", lambda seconds: None)

    runner = CliRunner()
    result = runner.invoke(tp_file.file, ["dump", "--wait", local])

    assert result.exit_code == 0, result.output
    with open(local + ".tpf") as fh:
        recorded = toml.load(fh)
    assert recorded["media_entry_id"] == "m-real-id"
    assert fake_course.calls == 3  # initial fetch + 2 retries before resolving
