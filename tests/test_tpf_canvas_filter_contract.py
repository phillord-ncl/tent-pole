"""Confirms tent_pole.file's .tpf output is actually consumable by
tent_pole.canvas_filter's image_filter/link_filter -- a real, enforced
integration test now that both live in the same repo. Before the
canvas-filter absorption feature, this used to just pin the set of .tpf
keys canvas-filter's separate repo depended on (confirmed by hand
against its source), since there was no way to run its actual code
here. See claude_redesign.md's canvas-filter section for why that used
to matter: dropping the unused "uuid" key during the state-manifest
feature was safe, but only because it was checked by hand first."""

import toml
import panflute as pf

from tests.test_file import FakeCanvasFile, FakeCourseForFile, write_local_file

from tent_pole import canvas_filter
from tent_pole import file as tp_file


def write_tpf_from_real_data(local, fake_course):
    data = tp_file.__data(local, fake_course)
    with open(local + ".tpf", "w") as fh:
        toml.dump(data, fh)
    return data


def test_file_data_is_consumable_by_image_filter(tmp_path):
    local = write_local_file(tmp_path / "diagram.png")
    canvas_file = FakeCanvasFile("diagram.png", size=100, id=7)
    fake_course = FakeCourseForFile([canvas_file])
    write_tpf_from_real_data(local, fake_course)

    elem = pf.Image(pf.Str("x"), url=local, title="x")
    result = canvas_filter.image_filter(elem, doc=None)

    assert isinstance(result, pf.RawInline)
    assert "courses/{}/files/{}/preview".format(fake_course.id, canvas_file.id) in result.text


def test_file_data_is_consumable_by_link_filter(tmp_path):
    local = write_local_file(tmp_path / "handout.pdf")
    canvas_file = FakeCanvasFile("handout.pdf", size=100, id=99)
    fake_course = FakeCourseForFile([canvas_file])
    write_tpf_from_real_data(local, fake_course)

    elem = pf.Link(pf.Str("x"), url=local)
    result = canvas_filter.link_filter(elem, doc=None)

    assert result.url == "../files/{}/download".format(canvas_file.id)
