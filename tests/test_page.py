from tent_pole import config, page


def test_canvasname_from_path_strips_directory_and_extension():
    assert page.canvasname_from_path("/a/b/test-1.html") == "test-1"


def test_canvasname_from_path_replaces_underscores_with_hyphens():
    assert page.canvasname_from_path("my_test_page.md") == "my-test-page"


def test_canvasname_from_path_no_extension():
    assert page.canvasname_from_path("README") == "README"


class FakePage:
    def __init__(self, page_id=1, url="test-1", title="Test 1",
                 updated_at="2026-01-01T00:00:00Z", last_edited_by=None):
        self.page_id = page_id
        self.url = url
        self.title = title
        self.updated_at = updated_at
        self.last_edited_by = last_edited_by


class FakeCourseForPage:
    def __init__(self, page_obj):
        self._page = page_obj

    def get_page(self, canvasname):
        return self._page


def write_local_file(path, content=b"<p>hello</p>"):
    path.write_bytes(content)
    return str(path)


def test_page_metadata_includes_hash_and_editor(tmp_path):
    local = write_local_file(tmp_path / "test-1.html")
    fake_page = FakePage(last_edited_by={"id": 5272, "display_name": "Phillip Lord"})

    data = page.__page_metadata(local, fake_page)

    assert data["hash"] == page.manifest.hash_file(local)
    assert data["page_id"] == 1
    assert data["last_edited_by"] == {"id": 5272, "display_name": "Phillip Lord"}


def test_page_metadata_handles_never_edited_page(tmp_path):
    """A freshly created page (title set, no body edit yet) has
    last_edited_by = None -- must not crash."""
    local = write_local_file(tmp_path / "test-1.html")
    fake_page = FakePage(last_edited_by=None)

    data = page.__page_metadata(local, fake_page)

    assert data["last_edited_by"] == {"id": None, "display_name": None}


def test_local_drift_none_when_unchanged(tmp_path):
    local = write_local_file(tmp_path / "test-1.html")
    recorded = {"hash": page.manifest.hash_file(local)}

    assert page.__local_drift(local, recorded) is None


def test_local_drift_detects_changed_file(tmp_path):
    local_path = tmp_path / "test-1.html"
    local = write_local_file(local_path, b"<p>original</p>")
    recorded = {"hash": page.manifest.hash_file(local)}

    write_local_file(local_path, b"<p>edited</p>")

    assert page.__local_drift(local, recorded) is not None


def test_local_drift_flags_missing_recorded_hash(tmp_path):
    local = write_local_file(tmp_path / "test-1.html")

    assert page.__local_drift(local, {}) is not None


def test_remote_drift_none_when_editor_matches_recorded(tmp_path, monkeypatch):
    local = write_local_file(tmp_path / "test-1.html")
    recorded = {"last_edited_by": {"id": 5272, "display_name": "Phillip Lord"}}
    fake_course = FakeCourseForPage(
        FakePage(last_edited_by={"id": 5272, "display_name": "Phillip Lord"})
    )
    monkeypatch.setattr(page.course, "course_obj", lambda: fake_course)

    assert page.__remote_drift(local, recorded) is None


def test_remote_drift_detects_editor_change(tmp_path, monkeypatch):
    local = write_local_file(tmp_path / "test-1.html")
    recorded = {"last_edited_by": {"id": 5272, "display_name": "Phillip Lord"}}
    fake_course = FakeCourseForPage(
        FakePage(last_edited_by={"id": 9999, "display_name": "A Colleague"})
    )
    monkeypatch.setattr(page.course, "course_obj", lambda: fake_course)

    assert page.__remote_drift(local, recorded) is not None


def test_remote_drift_falls_back_to_current_user_when_no_baseline(tmp_path, monkeypatch):
    local = write_local_file(tmp_path / "test-1.html")
    recorded = {}  # no baseline last_edited_by recorded at all
    fake_course = FakeCourseForPage(
        FakePage(last_edited_by={"id": 9999, "display_name": "A Colleague"})
    )
    monkeypatch.setattr(page.course, "course_obj", lambda: fake_course)
    monkeypatch.setattr(config, "config_current_user_id", lambda: 5272)

    assert page.__remote_drift(local, recorded) is not None


def test_remote_drift_no_baseline_but_current_user_matches(tmp_path, monkeypatch):
    local = write_local_file(tmp_path / "test-1.html")
    recorded = {}
    fake_course = FakeCourseForPage(
        FakePage(last_edited_by={"id": 5272, "display_name": "Phillip Lord"})
    )
    monkeypatch.setattr(page.course, "course_obj", lambda: fake_course)
    monkeypatch.setattr(config, "config_current_user_id", lambda: 5272)

    assert page.__remote_drift(local, recorded) is None
