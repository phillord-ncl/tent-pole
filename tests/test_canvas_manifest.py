import datetime

import pytest
import toml

from tent_pole import file as tp_file
from tent_pole import page

pytestmark = pytest.mark.canvas


def test_page_manifest_cycle(sandbox_course, tmp_path, monkeypatch):
    """push -> dump -> check/verify pass -> local edit -> check/verify
    correctly detect the drift. Real push against the sandbox course, no
    mocking -- see claude_redesign.md's state/manifest section."""
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
    assert page.__remote_drift(str(local), recorded) is None

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
