import toml
from click.testing import CliRunner

from tent_pole import page


class FakePage:
    page_id = 1
    url = "example"
    title = "Example"
    updated_at = "2026-01-01T00:00:00Z"
    body = "<p>hi</p>"

    def __init__(self, last_edited_by=None):
        self.last_edited_by = last_edited_by or {"id": 1, "display_name": "Someone"}
        self.edit_calls = []

    def edit(self, **kwargs):
        self.edit_calls.append(kwargs)


class FakeCourse:
    def __init__(self, page=None):
        self._page = page or FakePage()

    def get_page(self, canvasname):
        return self._page

    def get_pages(self):
        return [self._page]


def test_dump_writes_tpp_stamp_file(tmp_path, monkeypatch):
    """Integration test (real CLI dispatch + real file I/O together) that
    needs no *actual* Canvas access, so it isn't marked `canvas` and runs
    by default alongside the unit tests -- course.course_obj() is mocked
    out rather than hitting the network, since dump() now fetches the
    page's real metadata (see the state-manifest feature)."""
    monkeypatch.setattr(page.course, "course_obj", lambda: FakeCourse())

    target = tmp_path / "example.html"
    target.write_text("<p>hi</p>")

    runner = CliRunner()
    result = runner.invoke(page.page, ["dump", str(target)])

    assert result.exit_code == 0
    assert (tmp_path / "example.tpp").exists()


def write_tpp(path, last_edited_by):
    with open(page.__tpp_path(str(path)), "w") as fh:
        toml.dump({
            "hash": "irrelevant-to-remote-drift",
            "compiled_at": None,
            "last_edited_by": last_edited_by,
        }, fh)


def test_push_skips_drift_check_when_no_tpp_exists(tmp_path, monkeypatch):
    """A first-ever push has no baseline to drift from -- it must
    succeed rather than trying (and failing) to load a .tpp that has
    never been written yet."""
    fake_page = FakePage(last_edited_by={"id": 1, "display_name": "Someone"})
    monkeypatch.setattr(page.course, "course_obj", lambda: FakeCourse(fake_page))

    target = tmp_path / "example.html"
    target.write_text("<p>hi</p>")

    result = CliRunner().invoke(page.page, ["push", str(target)])

    assert result.exit_code == 0, result.output
    assert len(fake_page.edit_calls) == 1


def test_push_succeeds_when_no_remote_drift(tmp_path, monkeypatch):
    fake_page = FakePage(last_edited_by={"id": 1, "display_name": "Someone"})
    monkeypatch.setattr(page.course, "course_obj", lambda: FakeCourse(fake_page))

    target = tmp_path / "example.html"
    target.write_text("<p>hi</p>")
    write_tpp(target, last_edited_by={"id": 1, "display_name": "Someone"})

    result = CliRunner().invoke(page.page, ["push", str(target)])

    assert result.exit_code == 0, result.output
    assert len(fake_page.edit_calls) == 1


def test_push_aborts_on_remote_editor_drift(tmp_path, monkeypatch):
    """The whole point of #15: someone else has edited the page on
    Canvas since the last push/dump -- push must refuse rather than
    silently overwriting their edit."""
    fake_page = FakePage(last_edited_by={"id": 2, "display_name": "Someone Else"})
    monkeypatch.setattr(page.course, "course_obj", lambda: FakeCourse(fake_page))

    target = tmp_path / "example.html"
    target.write_text("<p>hi</p>")
    write_tpp(target, last_edited_by={"id": 1, "display_name": "Someone"})

    result = CliRunner().invoke(page.page, ["push", str(target)])

    assert result.exit_code != 0
    assert "Someone Else" in result.output
    assert fake_page.edit_calls == []


def test_push_force_overwrites_despite_remote_drift(tmp_path, monkeypatch):
    fake_page = FakePage(last_edited_by={"id": 2, "display_name": "Someone Else"})
    monkeypatch.setattr(page.course, "course_obj", lambda: FakeCourse(fake_page))

    target = tmp_path / "example.html"
    target.write_text("<p>hi</p>")
    write_tpp(target, last_edited_by={"id": 1, "display_name": "Someone"})

    result = CliRunner().invoke(page.page, ["push", "--force", str(target)])

    assert result.exit_code == 0, result.output
    assert len(fake_page.edit_calls) == 1
