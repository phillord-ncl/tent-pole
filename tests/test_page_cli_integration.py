from click.testing import CliRunner

from tent_pole import page


class FakePage:
    page_id = 1
    url = "example"
    title = "Example"
    updated_at = "2026-01-01T00:00:00Z"
    last_edited_by = {"id": 1, "display_name": "Someone"}


class FakeCourse:
    def get_page(self, canvasname):
        return FakePage()


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
