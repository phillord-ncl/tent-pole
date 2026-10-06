import toml
from click.testing import CliRunner

from tent_pole import file as tp_file


class FakeCanvasFile:
    def __init__(self, filename, size=100, content=b"file content",
                 uuid="uuid-1", id=1, media_entry_id=None, folder_id=1):
        self.filename = filename
        self.size = size
        self._content = content
        self.uuid = uuid
        self.id = id
        self.media_entry_id = media_entry_id
        self.folder_id = folder_id
        self.__dict__["content-type"] = "text/plain"

    def get_contents(self, binary=False):
        return self._content if binary else self._content.decode()


class FakeCourseForFile:
    def __init__(self, files, folders=None):
        self.id = 999
        self._files = files
        self.upload_calls = []
        self._folders = (
            folders
            if folders is not None
            else [FakeCanvasFolder("tent-pole", 1, "course files/tent-pole")]
        )

    def get_files(self):
        return self._files

    def get_folders(self):
        return self._folders

    def upload(self, filename, **kwargs):
        self.upload_calls.append((filename, kwargs))
        return True, {}


class FakeCanvasFolder:
    def __init__(self, name, id, full_name, parent_folder_id=None):
        self.name = name
        self.id = id
        self.full_name = full_name
        self.parent_folder_id = parent_folder_id

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
        self._folders = [
            FakeCanvasFolder("tent-pole", 1, "course files/tent-pole")
        ]

    def get_folders(self):
        return self._folders

    def get_files(self):
        self.calls += 1
        media_entry_id = "maybe" if self.calls <= self.resolves_after else "m-real-id"
        return [FakeCanvasFile(self.filename, media_entry_id=media_entry_id)]


def write_local_file(path, content=b"file content"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return str(path)


def test_data_includes_hash_and_size(tmp_path):
    local = write_local_file(tmp_path / "example.txt")
    canvas_file = FakeCanvasFile("example.txt", size=len(b"file content"))
    fake_course = FakeCourseForFile([canvas_file])

    data = tp_file.__data(local, fake_course)

    assert data["hash"] == tp_file.manifest.hash_file(local)
    assert data["size"] == len(b"file content")
    assert data["folder_id"] == 1


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
    landing in Canvas's generic "unfiled" folder like everything else.

    Also asserts on_duplicate="overwrite": Canvas's own upload API
    defaults to "rename" when this isn't passed, leaving any existing
    same-named file untouched and silently creating a second copy
    instead of replacing it -- confirmed against a real course, files
    pushed without this accumulate duplicates on every re-push. Always
    correct to overwrite here specifically because every push is
    scoped to TENT_POLE_FOLDER, so a same-named collision there is
    never an unrelated file."""
    local = write_local_file(tmp_path / "example.txt")
    fake_course = FakeCourseForFile([])
    monkeypatch.setattr(tp_file.course, "course_obj", lambda: fake_course)

    runner = CliRunner()
    result = runner.invoke(tp_file.file, ["push", local])

    assert result.exit_code == 0, result.output
    assert len(fake_course.upload_calls) == 1
    uploaded_filename, kwargs = fake_course.upload_calls[0]
    assert uploaded_filename == local
    assert kwargs == {
        "parent_folder_path": tp_file.TENT_POLE_FOLDER,
        "on_duplicate": "overwrite",
    }
    assert tp_file.TENT_POLE_FOLDER == "tent-pole"


def test_push_preserves_nested_course_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    local = write_local_file(
        tmp_path / "01-first-version" / "HelloWorld.java",
        b"class HelloWorld {}",
    )
    fake_course = FakeCourseForFile([])
    monkeypatch.setattr(tp_file.course, "course_obj", lambda: fake_course)

    result = CliRunner().invoke(
        tp_file.file, ["push", "01-first-version/HelloWorld.java"]
    )

    assert result.exit_code == 0, result.output
    assert fake_course.upload_calls == [
        (
            "01-first-version/HelloWorld.java",
            {
                "parent_folder_path": "tent-pole/01-first-version",
                "on_duplicate": "overwrite",
            },
        )
    ]


def test_file_lookup_disambiguates_same_filename_by_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    first_local = write_local_file(
        tmp_path / "01-first-version" / "HelloWorld.java"
    )
    second_local = write_local_file(
        tmp_path / "02-personal-greeting" / "HelloWorld.java"
    )
    first = FakeCanvasFolder(
        "01-first-version", 2,
        "course files/tent-pole/01-first-version", 1
    )
    second = FakeCanvasFolder(
        "02-personal-greeting", 3,
        "course files/tent-pole/02-personal-greeting", 1
    )
    root = FakeCanvasFolder("tent-pole", 1, "course files/tent-pole")
    course = FakeCourseForFile(
        [
            FakeCanvasFile("HelloWorld.java", id=20, folder_id=2),
            FakeCanvasFile("HelloWorld.java", id=30, folder_id=3),
        ],
        folders=[root, first, second],
    )

    assert tp_file.__find_file("01-first-version/HelloWorld.java", course).id == 20
    assert tp_file.__find_file("02-personal-greeting/HelloWorld.java", course).id == 30
    assert tp_file.__data(first_local, course)["id"] == 20
    assert tp_file.__data(second_local, course)["id"] == 30


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
