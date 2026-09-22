import os
import shutil

import canvasapi.exceptions
import panflute as pf
import pytest
import toml

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


def test_image_filter_strips_canvas_editor_cruft(tmp_path):
    """A hand-authored (Canvas RCE) image carries editor/API bookkeeping
    -- the file id as #identifier, loading="lazy",
    data-api-endpoint/-returntype -- that pandoc would otherwise leak
    straight into the markdown as {#123 loading="lazy" ...} clutter."""
    context = make_context(tmp_path, files=[FakeCanvasFile("diagram.png", id=7)])
    elem = pf.Image(
        pf.Str("x"), url="https://canvas.test/courses/1/files/7/preview",
        identifier="7",
        attributes={"loading": "lazy", "api-endpoint": "https://canvas.test/api/v1/...",
                    "api-returntype": "File"},
    )

    result = cif.image_filter(elem, context)

    assert result.identifier == ""
    assert dict(result.attributes) == {}


def test_image_filter_keeps_width_and_height(tmp_path):
    context = make_context(tmp_path, files=[FakeCanvasFile("diagram.png", id=7)])
    elem = pf.Image(
        pf.Str("x"), url="https://canvas.test/courses/1/files/7/preview",
        attributes={"width": "400", "loading": "lazy"},
    )

    result = cif.image_filter(elem, context)

    assert dict(result.attributes) == {"width": "400"}


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


## GNU source-highlight (pre-Pygments) code blocks

LEGACY_HELLO_WORLD_HTML = (
    '<pre><tt><font color="#000000">1:</font> '
    '<b><font color="#0000FF">print</font></b>'
    '<font color="#990000">(</font>'
    '<font color="#FF0000">"Hello World"</font>'
    '<font color="#990000">)</font>\n'
    '<font color="#000000">2:</font> </tt></pre>'
)


def test_convert_unwraps_legacy_source_highlight_block():
    context = cif.ImportContext(courseobj=None, page_slugs=[], output_dir=".")
    markdown = cif.convert(LEGACY_HELLO_WORLD_HTML, context)

    assert 'print("Hello World")' in markdown
    assert "<font" not in markdown
    assert "1:" not in markdown


def test_convert_preserves_indentation_in_legacy_source_highlight_block():
    html = (
        '<pre><tt><font color="#000000">1:</font> '
        '<b><font color="#000080">def</font></b> f():\n'
        '<font color="#000000">2:</font>     '
        '<b><font color="#000080">return</font></b> 1\n'
        '</tt></pre>'
    )
    context = cif.ImportContext(courseobj=None, page_slugs=[], output_dir=".")
    markdown = cif.convert(html, context)

    assert "def f():" in markdown
    assert "    return 1" in markdown


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


## Reconstructing {include=...} from canvas_filter's own real output

def build_include_html(source_dir, filename="demo.py", source="print(1)\n",
                        file_id=55, output=False, stout=False, crash=False,
                        hide_crash=False):
    """The real HTML canvas_filter.code_filter produces for an
    include='d code block, built the same way canvas_filter's own tests
    do (a real local file + its .tpf), so the reconstruction is proven
    against actual forward-filter output rather than a hand-guessed
    shape."""
    source_path = source_dir / filename
    source_path.write_text(source)
    with open(str(source_path) + ".tpf", "w") as fh:
        toml.dump({"id": file_id}, fh)

    attributes = {"include": str(source_path)}
    stem = str(source_path.with_suffix(""))
    if output:
        attributes["output"] = "true"
        (source_dir / (source_path.stem + ".out")).write_text("1\n")
    if stout:
        attributes["stout"] = "true"
        (source_dir / (source_path.stem + ".stout")).write_text(">>> print(1)\n1\n")
    if crash:
        attributes["crash"] = "true"
        (source_dir / (source_path.stem + ".crash")).write_text("Traceback...\n")
    if hide_crash:
        attributes["hide_crash"] = "true"

    elem = pf.CodeBlock("", classes=["python"], attributes=attributes)
    blocks = canvas_filter.code_filter(elem, doc=None)
    return pf.convert_text(pf.Doc(*blocks), input_format="panflute", output_format="html")


def test_convert_reconstructs_bare_include_directive(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    html = build_include_html(source_dir, filename="demo.py", file_id=55)

    context = cif.ImportContext(
        FakeCourseForImport([FakeCanvasFile("demo.py", content=b"print(1)\n", id=55)]),
        page_slugs=[], output_dir=str(target_dir),
    )
    markdown = cif.convert(html, context)

    assert '{.python include="demo.py"}' in markdown
    assert "print(1)" not in markdown  # not a literal copy of the source
    assert "Taken from" not in markdown
    assert (target_dir / "demo.py").read_text() == "print(1)\n"


def test_convert_reconstructs_include_directive_from_legacy_take_from_wording(tmp_path):
    """Real courses that have been live a while carry pages built by an
    older canvas_filter that phrased the link "Take from: <file>" (no
    "n") -- confirmed against real content, not assumed. Must not
    silently fall back to a literal code block just because the label
    text changed at some point in tent-pole's own history."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    html = build_include_html(source_dir, filename="demo.py", file_id=55)
    html = html.replace("Taken from: ", "Take from: ")

    context = cif.ImportContext(
        FakeCourseForImport([FakeCanvasFile("demo.py", content=b"print(1)\n", id=55)]),
        page_slugs=[], output_dir=str(target_dir),
    )
    markdown = cif.convert(html, context)

    assert '{.python include="demo.py"}' in markdown


def test_convert_reconstructs_include_with_output_attribute(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    html = build_include_html(source_dir, filename="demo.py", file_id=55, output=True)

    context = cif.ImportContext(
        FakeCourseForImport([FakeCanvasFile("demo.py", content=b"print(1)\n", id=55)]),
        page_slugs=[], output_dir=str(target_dir),
    )
    markdown = cif.convert(html, context)

    assert 'include="demo.py"' in markdown
    assert 'output="true"' in markdown
    assert "Outputs:" not in markdown


def test_convert_reconstructs_output_attribute_from_legacy_no_colon_wording(tmp_path):
    """Real content shows the same older-canvas_filter wording drift
    here as "Take from: " vs "Taken from: " -- "Outputs"/"Prints"/
    "Crashes" with no trailing colon, confirmed against real content,
    not assumed."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    html = build_include_html(source_dir, filename="demo.py", file_id=55, output=True)
    html = html.replace("Outputs:", "Outputs")

    context = cif.ImportContext(
        FakeCourseForImport([FakeCanvasFile("demo.py", content=b"print(1)\n", id=55)]),
        page_slugs=[], output_dir=str(target_dir),
    )
    markdown = cif.convert(html, context)

    assert 'output="true"' in markdown


def test_convert_reconstructs_stout_and_crash_attributes(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    html = build_include_html(source_dir, filename="demo.py", file_id=55, stout=True, crash=True)

    context = cif.ImportContext(
        FakeCourseForImport([FakeCanvasFile("demo.py", content=b"print(1)\n", id=55)]),
        page_slugs=[], output_dir=str(target_dir),
    )
    markdown = cif.convert(html, context)

    assert 'stout="true"' in markdown
    assert 'crash="true"' in markdown
    assert "Prints:" not in markdown
    assert "Crashes:" not in markdown


def test_convert_infers_no_language_class_for_an_unknown_extension(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    html = build_include_html(source_dir, filename="demo.txt", source="hello\n", file_id=55)

    context = cif.ImportContext(
        FakeCourseForImport([FakeCanvasFile("demo.txt", content=b"hello\n", id=55)]),
        page_slugs=[], output_dir=str(target_dir),
    )
    markdown = cif.convert(html, context)

    assert 'include="demo.txt"' in markdown
    assert ".python" not in markdown


def test_convert_falls_back_to_literal_code_when_include_file_missing(tmp_path):
    """The include='d file's own .tpf id no longer resolves on Canvas
    (same real-world drift as any other file link) -- nothing was
    downloaded to reconstruct include= against, so the best-effort
    literal code block (with its now-inert "Taken from:" link) is kept
    instead of inventing a reference to a file that was never fetched."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    html = build_include_html(source_dir, filename="demo.py", file_id=404)

    context = cif.ImportContext(FakeCourseForImport([]), page_slugs=[], output_dir=str(target_dir))
    markdown = cif.convert(html, context)

    assert "include=" not in markdown
    assert "print(1)" in markdown


## Video embeds -- canvas_filter's mp4 -> <iframe data-media-id=...>
## has no download path at all (no media-object API support), and left
## alone pandoc's HTML reader silently drops any tag it doesn't
## recognise, iframe included -- confirmed against real Canvas content.

VIDEO_IFRAME_HTML = (
    '<p>This is a link to a video</p>\n'
    '<p>\n<iframe style="width: 400px; height: 225px; display: inline-block;" '
    'title="Video player for demo.mp4" data-media-type="video" '
    'src="https://canvas.test/media_objects_iframe/m-abc123?type=video" '
    'allowfullscreen="allowfullscreen" allow="fullscreen" '
    'data-media-id="m-abc123" loading="lazy"></iframe>\n</p>\n'
    '<p>Complete</p>\n'
    '<script src="https://cdn.test/theme-injected.js"></script>'
)


def test_convert_does_not_silently_drop_a_video_embed(capsys):
    context = cif.ImportContext(courseobj=None, page_slugs=[], output_dir=".")
    markdown = cif.convert(VIDEO_IFRAME_HTML, context)

    assert "This is a link to a video" in markdown
    assert "Complete" in markdown
    assert "demo.mp4" in markdown
    assert "<iframe" not in markdown
    ## Regression: the fixture's iframe is already inside its own <p>
    ## (real Canvas content wraps embeds this way) -- an earlier version
    ## of the replacement nested a block <p> inside that one, leaving
    ## the original closing </p> dangling with nothing left to match,
    ## which survived as literal "</p>" text once +raw_html stopped
    ## silently dropping unmatched tags.
    assert "</p>" not in markdown
    captured = capsys.readouterr()
    assert "demo.mp4" in captured.out


def test_convert_strips_theme_injected_script_tags():
    context = cif.ImportContext(courseobj=None, page_slugs=[], output_dir=".")
    markdown = cif.convert(VIDEO_IFRAME_HTML, context)

    assert "script" not in markdown
    assert "theme-injected" not in markdown
