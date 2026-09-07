"""Pins the .tpf keys that canvas-filter (a separate repo,
~/src/python/canvas-filter) actually depends on, confirmed against its
real source (canvas_filter/__init__.py) rather than assumption:

    include_url = "../files/{}/download".format(str(tpf(include).get("id")))
    ...format(uuid=tpf_data.get("media_entry_id"))
    ...format(id=tpf_data.get("id"), ..., course=tpf_data.get("course"))

canvas-filter has no tests of its own, and this contract is otherwise
completely implicit -- a change here could silently break it with
nothing catching it (this happened for real once already: dropping the
unused "uuid" key during the state-manifest feature was safe, but only
because it was checked by hand against canvas-filter's source first).
See claude_redesign.md for the plan to absorb canvas-filter outright,
which would let this contract be enforced by a real shared test instead
of a comment like this one."""

from tests.test_file import FakeCanvasFile, FakeCourseForFile, write_local_file

from tent_pole import file as tp_file

CANVAS_FILTER_REQUIRED_TPF_KEYS = {"id", "media_entry_id", "course"}


def test_tpf_data_includes_every_key_canvas_filter_reads(tmp_path):
    local = write_local_file(tmp_path / "example.txt")
    canvas_file = FakeCanvasFile("example.txt")
    fake_course = FakeCourseForFile([canvas_file])

    data = tp_file.__data(local, fake_course)

    missing = CANVAS_FILTER_REQUIRED_TPF_KEYS - data.keys()
    assert not missing, (
        "canvas-filter reads these .tpf keys directly (see module "
        "docstring) -- removing one would silently break it: {}"
    ).format(missing)
