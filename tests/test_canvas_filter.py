import datetime

import panflute as pf
import toml

from tent_pole import canvas_filter


def write_tpf(path, data):
    with open(str(path) + ".tpf", "w") as fh:
        toml.dump(data, fh)


def write_tpp(path, data):
    with open(str(path) + ".tpp", "w") as fh:
        toml.dump(data, fh)


## highlight_source (replaces GNU source-highlight with Pygments)

def test_highlight_source_highlights_recognized_language():
    html = canvas_filter.highlight_source("def f(): pass", "python")
    ## Pygments wraps recognized-language keywords in styled spans
    assert "<span" in html
    assert "def" in html


def test_highlight_source_falls_back_to_plain_for_unknown_language():
    """The whole point of replacing source-highlight: an unrecognised
    language must not crash, and shouldn't get spurious highlighting."""
    html = canvas_filter.highlight_source("some plain content", "not-a-real-language")
    assert "some plain content" in html
    ## no keyword/token spans wrapping the actual content (TextLexer)
    assert "<span" not in html.replace("<span></span>", "")


## code_filter

def test_code_filter_no_language_wraps_plain_pre_code():
    elem = pf.CodeBlock("plain text", classes=[])
    result = canvas_filter.code_filter(elem, doc=None)
    raw = result[0]
    assert isinstance(raw, pf.RawBlock)
    assert raw.text == "<pre><code>plain text\n</code></pre>"


def test_code_filter_with_language_highlights_via_pygments():
    elem = pf.CodeBlock("def f(): pass", classes=["python"])
    result = canvas_filter.code_filter(elem, doc=None)
    raw = result[0]
    assert isinstance(raw, pf.RawBlock)
    assert "<span" in raw.text


def test_code_filter_include_links_to_tpf_file_id(tmp_path):
    source = tmp_path / "snippet.py"
    source.write_text("print('hi')")
    write_tpf(source, {"id": 42})

    elem = pf.CodeBlock("", classes=["python"], attributes={"include": str(source)})
    result = canvas_filter.code_filter(elem, doc=None)

    ## RawBlock (highlighted) + Para(Link) pointing at the file id
    assert len(result) == 2
    link_para = result[1]
    assert isinstance(link_para, pf.Para)
    link = link_para.content[0]
    assert isinstance(link, pf.Link)
    assert link.url == "../files/42/download"


## link_filter

def test_link_filter_leaves_external_urls_unchanged():
    elem = pf.Link(pf.Str("x"), url="https://example.com/foo")
    result = canvas_filter.link_filter(elem, doc=None)
    assert result.url == "https://example.com/foo"


def test_link_filter_leaves_extensionless_local_links_unchanged():
    elem = pf.Link(pf.Str("x"), url="some-page")
    result = canvas_filter.link_filter(elem, doc=None)
    assert result.url == "some-page"


def test_link_filter_treats_html_extensioned_link_as_page_reference():
    """See tent-pole issue #23: a link spelled out with the target's
    .html (or .md) is still a page reference, not a file attachment --
    there is no intro.html.tpf, intro.html was never pushed via file
    push, it's a page. Falls back to the bare name (extension
    stripped), same as the no-extension form, when not dumped yet."""
    elem = pf.Link(pf.Str("x"), url="intro.html")
    result = canvas_filter.link_filter(elem, doc=None)
    assert result.url == "intro"


def test_link_filter_treats_md_extensioned_link_as_page_reference():
    elem = pf.Link(pf.Str("x"), url="intro.md")
    result = canvas_filter.link_filter(elem, doc=None)
    assert result.url == "intro"


def test_link_filter_resolves_html_extensioned_link_to_its_dumped_real_url(tmp_path):
    page = tmp_path / "intro"
    write_tpp(page, {"url": "intro-2"})

    elem = pf.Link(pf.Str("x"), url=str(page) + ".html")
    result = canvas_filter.link_filter(elem, doc=None)

    assert result.url == "intro-2"


def test_link_filter_resolves_page_link_to_its_dumped_real_url(tmp_path):
    """See tent-pole issue #29: Canvas reserves a deleted page's slug
    for undelete, so a page's real url can diverge from the name a
    link was authored with. Its .tpp (written by page dump) records
    the real url once it's known -- resolve to that rather than the
    raw link text, same as an image/file link resolves via .tpf."""
    page = tmp_path / "some-page"
    write_tpp(page, {"url": "some-page-2"})

    elem = pf.Link(pf.Str("x"), url=str(page))
    result = canvas_filter.link_filter(elem, doc=None)

    assert result.url == "some-page-2"


def test_link_filter_resolves_page_link_with_fragment_to_its_dumped_real_url(tmp_path):
    """A link to a specific heading (some-page#some-heading) needs
    some-page.tpp, not some-page#some-heading.tpp -- the fragment
    isn't part of the page's own url, and must survive onto the
    resolved link."""
    page = tmp_path / "some-page"
    write_tpp(page, {"url": "some-page-2"})

    elem = pf.Link(pf.Str("x"), url=str(page) + "#some-heading")
    result = canvas_filter.link_filter(elem, doc=None)

    assert result.url == "some-page-2#some-heading"


def test_link_filter_leaves_page_link_unchanged_when_not_dumped_yet(tmp_path):
    """No .tpp yet (e.g. the target's own first build hasn't run) --
    a page-to-page link is deliberately not a .tpd build dependency,
    so there's no ordering guarantee it exists. Falls back to the raw
    link text, same as before this resolution existed at all."""
    page = tmp_path / "not-dumped-yet"

    elem = pf.Link(pf.Str("x"), url=str(page))
    result = canvas_filter.link_filter(elem, doc=None)

    assert result.url == str(page)


def test_link_filter_mp4_becomes_video_iframe(tmp_path):
    video = tmp_path / "clip.mp4"
    write_tpf(video, {"media_entry_id": "m123"})

    elem = pf.Link(pf.Str("x"), url=str(video))
    result = canvas_filter.link_filter(elem, doc=None)

    assert isinstance(result, pf.RawInline)
    assert "m123" in result.text
    assert "media_objects_iframe" in result.text


def test_link_filter_other_local_file_links_via_tpf_id(tmp_path):
    doc_file = tmp_path / "handout.pdf"
    write_tpf(doc_file, {"id": 99})

    elem = pf.Link(pf.Str("x"), url=str(doc_file))
    result = canvas_filter.link_filter(elem, doc=None)

    assert result.url == "../files/99/download"


## image_filter

def test_image_filter_builds_canvas_preview_url(tmp_path):
    image = tmp_path / "diagram.png"
    write_tpf(image, {"id": 7, "course": 16807})

    elem = pf.Image(pf.Str("My Diagram"), url=str(image), title="My Diagram")
    result = canvas_filter.image_filter(elem, doc=None)

    assert isinstance(result, pf.RawInline)
    assert "courses/16807/files/7/preview" in result.text


def test_image_filter_uses_bracket_text_as_alt(tmp_path):
    """Regression test: elem.title is only the optional quoted string
    after the url (![alt](url "title")), not the bracket text -- using
    it for alt= silently produced alt="" for the plain ![alt](url) form
    used almost everywhere in the real course repos."""
    image = tmp_path / "diagram.png"
    write_tpf(image, {"id": 7, "course": 16807})

    elem = pf.Image(pf.Str("Sign"), pf.Space(), pf.Str("Up"), url=str(image))
    result = canvas_filter.image_filter(elem, doc=None)

    assert 'alt="Sign Up"' in result.text


def test_image_filter_prefers_explicit_alt_attribute(tmp_path):
    """The ![](url){alt="..."} form -- empty bracket content avoids
    pandoc's implicit-figure/caption promotion of a standalone image,
    so the alt text has to come from the attribute instead."""
    image = tmp_path / "diagram.png"
    write_tpf(image, {"id": 7, "course": 16807})

    elem = pf.Image(url=str(image), attributes={"alt": "Explicit alt text"})
    result = canvas_filter.image_filter(elem, doc=None)

    assert 'alt="Explicit alt text"' in result.text


def test_image_filter_falls_back_to_title_when_no_content_or_attribute(tmp_path):
    image = tmp_path / "diagram.png"
    write_tpf(image, {"id": 7, "course": 16807})

    elem = pf.Image(url=str(image), title="Only a title")
    result = canvas_filter.image_filter(elem, doc=None)

    assert 'alt="Only a title"' in result.text


## canvas_filter dispatcher

def test_canvas_filter_dispatches_by_element_type(tmp_path):
    image = tmp_path / "diagram.png"
    write_tpf(image, {"id": 7, "course": 1})
    img_elem = pf.Image(pf.Str("x"), url=str(image), title="x")
    assert isinstance(canvas_filter.canvas_filter(img_elem, doc=None), pf.RawInline)

    code_elem = pf.CodeBlock("x", classes=[])
    assert canvas_filter.canvas_filter(code_elem, doc=None) is not None

    ## Uninteresting element types are left alone (returns None -> no change)
    para = pf.Para(pf.Str("hello"))
    assert canvas_filter.canvas_filter(para, doc=None) is None


## tent-pole tagging marker

def test_extract_compiled_at_finds_the_timestamp():
    html = '<p>hi</p><span data-tent-pole="managed" data-compiled-at="2026-09-07T00:00:00+00:00"></span>'
    assert canvas_filter.extract_compiled_at(html) == "2026-09-07T00:00:00+00:00"


def test_extract_compiled_at_none_when_marker_absent():
    assert canvas_filter.extract_compiled_at("<p>plain content, no marker</p>") is None


def test_add_tent_pole_marker_appends_span_with_valid_timestamp():
    doc = pf.Doc(pf.Para(pf.Str("hello")))
    canvas_filter.add_tent_pole_marker(doc)

    assert len(doc.content) == 2
    marker = doc.content[1]
    assert isinstance(marker, pf.RawBlock)
    assert 'data-tent-pole="managed"' in marker.text

    compiled_at = canvas_filter.extract_compiled_at(marker.text)
    assert compiled_at is not None
    datetime.datetime.fromisoformat(compiled_at)
