import os
import shutil

import canvasapi.exceptions
import panflute as pf
import pytest

from tent_pole import canvas_filter
from tent_pole import course_import_filter as cif

pandoc_missing = shutil.which("pandoc") is None
pytestmark = pytest.mark.skipif(pandoc_missing, reason="pandoc not installed")


class FakeCanvasFile:
    def __init__(self, filename, content=b"file content", id=1):
        self.filename = filename
        self.id = id
        self._content = content

    def get_contents(self, binary=False):
        return self._content if binary else self._content.decode()


class FakeCourseForImport:
    def __init__(self, files):
        self._files_by_id = {f.id: f for f in files}
        self.get_file_calls = []

    def get_file(self, file_id):
        self.get_file_calls.append(file_id)
        if int(file_id) not in self._files_by_id:
            raise canvasapi.exceptions.ResourceDoesNotExist("Not Found")
        return self._files_by_id[int(file_id)]


def make_context(tmp_path, files=(), page_slugs=()):
    return cif.ImportContext(
        FakeCourseForImport(list(files)), page_slugs, str(tmp_path)
    )


## ImportContext.download_file

def test_download_file_writes_content_under_its_canvas_filename(tmp_path):
    context = make_context(tmp_path, files=[FakeCanvasFile("diagram.png", id=7)])

    filename = context.download_file(7)

    assert filename == "diagram.png"
    assert (tmp_path / "diagram.png").read_bytes() == b"file content"


def test_download_file_dedups_repeated_ids(tmp_path):
    context = make_context(tmp_path, files=[FakeCanvasFile("diagram.png", id=7)])

    context.download_file(7)
    context.download_file(7)

    assert context.courseobj.get_file_calls == [7]


def test_download_file_returns_none_for_a_file_no_longer_on_canvas(tmp_path, capsys):
    context = make_context(tmp_path)

    filename = context.download_file(404)

    assert filename is None
    captured = capsys.readouterr()
    assert "404" in captured.out


def test_download_file_caches_a_missing_file_too(tmp_path):
    """A missing file must not be re-fetched (and re-warned about) on
    every reference to it -- the failure itself is cached, same as a
    successful download's filename."""
    context = make_context(tmp_path)

    context.download_file(404)
    context.download_file(404)

    assert context.courseobj.get_file_calls == [404]


def test_download_file_disambiguates_name_collision(tmp_path):
    (tmp_path / "diagram.png").write_bytes(b"already here, from another page")
    context = make_context(tmp_path, files=[FakeCanvasFile("diagram.png", id=7)])

    filename = context.download_file(7)

    assert filename == "diagram-2.png"
    assert (tmp_path / "diagram-2.png").read_bytes() == b"file content"


## image_filter

def test_image_filter_rewrites_to_local_downloaded_filename(tmp_path):
    context = make_context(tmp_path, files=[FakeCanvasFile("diagram.png", id=7)])
    elem = pf.Image(pf.Str("x"), url="https://canvas.test/courses/1/files/7/preview")

    result = cif.image_filter(elem, context)

    assert result.url == "diagram.png"


def test_image_filter_leaves_non_file_urls_unchanged():
    elem = pf.Image(pf.Str("x"), url="https://example.com/pic.png")
    assert cif.image_filter(elem, context=None) is None


def test_image_filter_leaves_url_unchanged_when_file_is_missing(tmp_path):
    context = make_context(tmp_path)
    url = "https://canvas.test/courses/1/files/404/preview"
    elem = pf.Image(pf.Str("x"), url=url)

    result = cif.image_filter(elem, context)

    assert result.url == url


## link_filter

def test_link_filter_rewrites_in_course_page_link_to_bare_slug(tmp_path):
    context = make_context(tmp_path, page_slugs=["some-page"])
    elem = pf.Link(pf.Str("x"), url="https://canvas.test/courses/1/pages/some-page")

    result = cif.link_filter(elem, context)

    assert result.url == "some-page"


def test_link_filter_preserves_fragment_on_in_course_page_link(tmp_path):
    context = make_context(tmp_path, page_slugs=["some-page"])
    elem = pf.Link(pf.Str("x"), url="https://canvas.test/courses/1/pages/some-page#heading")

    result = cif.link_filter(elem, context)

    assert result.url == "some-page#heading"


def test_link_filter_leaves_page_link_to_uncloned_page_untouched(tmp_path):
    context = make_context(tmp_path, page_slugs=["some-page"])
    url = "https://canvas.test/courses/1/pages/some-other-page"
    elem = pf.Link(pf.Str("x"), url=url)

    result = cif.link_filter(elem, context)

    assert result.url == url


def test_link_filter_downloads_file_link(tmp_path):
    context = make_context(tmp_path, files=[FakeCanvasFile("handout.pdf", id=99)])
    elem = pf.Link(pf.Str("x"), url="https://canvas.test/courses/1/files/99/download")

    result = cif.link_filter(elem, context)

    assert result.url == "handout.pdf"
    assert (tmp_path / "handout.pdf").exists()


def test_link_filter_leaves_external_link_untouched(tmp_path):
    context = make_context(tmp_path)
    elem = pf.Link(pf.Str("x"), url="https://example.com/foo")

    result = cif.link_filter(elem, context)

    assert result.url == "https://example.com/foo"


def test_link_filter_leaves_url_unchanged_when_file_is_missing(tmp_path):
    context = make_context(tmp_path)
    url = "https://canvas.test/courses/1/files/404/download"
    elem = pf.Link(pf.Str("x"), url=url)

    result = cif.link_filter(elem, context)

    assert result.url == url


## import_filter -- managed marker stripping

def test_import_filter_strips_managed_marker_paragraph(tmp_path):
    context = make_context(tmp_path)
    span = pf.Span(attributes={"style": "display:none", "tent-pole": "managed",
                                "compiled-at": "2026-01-01T00:00:00+00:00"})
    elem = pf.Para(span)

    result = cif.import_filter(elem, doc=None, context=context)

    assert result == []


def test_import_filter_leaves_ordinary_paragraph_untouched(tmp_path):
    context = make_context(tmp_path)
    elem = pf.Para(pf.Str("hello"))

    result = cif.import_filter(elem, doc=None, context=context)

    assert result is None


## Pygments highlight-block unwrapping

def test_import_filter_unwraps_pygments_highlight_block_to_plain_codeblock(tmp_path):
    context = make_context(tmp_path)
    original = "def f():\n    return 1\n"
    html = canvas_filter.highlight_source(original, "python")
    doc = pf.convert_text(html, input_format="html", output_format="panflute", standalone=True)
    div = doc.content[0]
    assert isinstance(div, pf.Div) and "highlight" in div.classes

    result = cif.import_filter(div, doc=doc, context=context)

    assert isinstance(result, pf.CodeBlock)
    assert result.text == original


## Round trip through the real forward filter, mirroring
## test_canvas_filter_pandoc_integration.py's own approach: the surest
## check that the reverse filter actually undoes what canvas_filter does
## is feeding it canvas_filter's own real output.

def test_convert_strips_marker_appended_by_forward_filter():
    doc = pf.Doc(pf.Para(pf.Str("hello")))
    canvas_filter.add_tent_pole_marker(doc)
    html = pf.convert_text(doc, input_format="panflute", output_format="html")

    context = cif.ImportContext(courseobj=None, page_slugs=[], output_dir=".")
    markdown = cif.convert(html, context)

    assert "hello" in markdown
    assert "tent-pole" not in markdown
    assert "display:none" not in markdown


def test_convert_downloads_image_produced_by_forward_image_filter(tmp_path):
    tpf_elem = pf.Image(pf.Str("A Diagram"), url="whatever", title="A Diagram")
    tpf_elem.attributes["alt"] = "A Diagram"

    ## Build the raw <img> the forward filter emits directly, rather than
    ## re-deriving config/.tpf plumbing just to call image_filter here.
    html = (
        '<img id="7" src="https://canvas.test/courses/16807/files/7/preview" '
        'alt="A Diagram" />'
    )

    context = cif.ImportContext(
        FakeCourseForImport([FakeCanvasFile("diagram.png", id=7)]),
        page_slugs=[], output_dir=str(tmp_path),
    )
    markdown = cif.convert(html, context)

    assert "diagram.png" in markdown
    assert (tmp_path / "diagram.png").exists()


def test_convert_unwraps_real_pygments_output_to_a_plain_code_block():
    original = "print('hi')\n"
    html = canvas_filter.highlight_source(original, "python")

    context = cif.ImportContext(courseobj=None, page_slugs=[], output_dir=".")
    markdown = cif.convert(html, context)

    assert "print('hi')" in markdown
    assert "style=" not in markdown
    assert "{." not in markdown  # no leftover bracketed-span syntax
