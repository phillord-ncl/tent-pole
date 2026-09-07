import datetime
import shutil
import subprocess

import pytest
import toml

from tent_pole import file as tp_file
from tent_pole import page

pytestmark = pytest.mark.canvas

pandoc_missing = shutil.which("pandoc") is None


def test_page_manifest_cycle(sandbox_course, tmp_path, monkeypatch):
    """push -> dump -> check/verify pass -> local edit -> check/verify
    correctly detect the drift. Real push against the sandbox course, no
    mocking."""
    monkeypatch.setattr(page.course, "course_obj", lambda: sandbox_course)

    local = tmp_path / "manifest-cycle-page.html"
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    local.write_text("<p>manifest cycle check: {}</p>".format(timestamp))

    canvasname = page.canvasname_from_path(str(local))
    pushed = page.__get_create_page(sandbox_course, canvasname)
    with open(local) as fh:
        pushed.edit(wiki_page={"body": fh.read()})

    pageobj = sandbox_course.get_page(canvasname)
    with open(page.__tpp_path(str(local)), "w") as fh:
        toml.dump(page.__page_metadata(str(local), pageobj), fh)

    recorded = page.__load_tpp(str(local))
    assert page.__local_drift(str(local), recorded) is None
    assert page.__remote_drift(str(local), recorded) == []

    local.write_text("<p>manifest cycle check: EDITED LOCALLY</p>")
    assert page.__local_drift(str(local), recorded) is not None


def test_file_manifest_cycle(sandbox_course, tmp_path, monkeypatch):
    """push -> dump -> check/verify pass -> local edit -> check detects
    it. Real push against the sandbox course, no mocking."""
    local = tmp_path / "manifest-cycle-file.txt"
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    local.write_text("manifest cycle check: {}".format(timestamp))

    sandbox_course.upload(str(local))
    recorded = tp_file.__data(str(local), sandbox_course)

    assert tp_file.__local_drift(str(local), recorded) is None
    assert tp_file.__remote_drift(str(local), recorded, sandbox_course) is None
    assert (
        tp_file.__remote_drift(str(local), recorded, sandbox_course, deep=True)
        is None
    )

    local.write_text("manifest cycle check: EDITED LOCALLY")
    assert tp_file.__local_drift(str(local), recorded) is not None


@pytest.mark.skipif(pandoc_missing, reason="pandoc not installed")
def test_compiled_at_drift_catches_a_stale_repush(sandbox_course, tmp_path, monkeypatch):
    """The real scenario __compiled_at_drift exists for: a page gets
    rebuilt (new compiled-at marker) and pushed, but dump doesn't get
    re-run afterward -- .tpp still records the OLD build's marker while
    Canvas has the NEW one. __editor_drift alone can't catch this, since
    both pushes are tent-pole's own identity."""
    monkeypatch.setattr(page.course, "course_obj", lambda: sandbox_course)

    md = tmp_path / "marker-cycle.md"
    html_path = tmp_path / "marker-cycle.html"
    canvasname = page.canvasname_from_path(str(html_path))

    def render():
        md.write_text("# Hello\n")
        subprocess.run(
            ["pandoc", str(md), "--filter=canvas-filter", "-o", str(html_path)],
            check=True,
        )
        return html_path.read_text()

    first_html = render()
    pushed = page.__get_create_page(sandbox_course, canvasname)
    pushed.edit(wiki_page={"body": first_html})

    pageobj = sandbox_course.get_page(canvasname)
    with open(page.__tpp_path(str(html_path)), "w") as fh:
        toml.dump(page.__page_metadata(str(html_path), pageobj), fh)
    recorded = page.__load_tpp(str(html_path))

    assert recorded["compiled_at"] is not None
    assert page.__remote_drift(str(html_path), recorded) == []

    ## Rebuild (new compiled-at) and push directly, WITHOUT re-running
    ## dump -- .tpp still has the old build's marker recorded.
    second_html = render()
    assert second_html != first_html  # genuinely a different build
    pageobj.edit(wiki_page={"body": second_html})

    problems = page.__remote_drift(str(html_path), recorded)
    assert problems != []
    assert any("compiled-at" in p for p in problems)
