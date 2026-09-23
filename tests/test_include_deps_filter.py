import panflute as pf

from tent_pole import include_deps_filter as deps_filter


def make_doc(*blocks):
    return pf.Doc(*blocks)


## is_local_asset_url

def test_is_local_asset_url_false_for_external():
    assert deps_filter.is_local_asset_url("https://example.com/foo.pdf") is False


def test_is_local_asset_url_false_for_extensionless_page_reference():
    assert deps_filter.is_local_asset_url("introduction") is False


def test_is_local_asset_url_false_for_md_or_html_page_reference():
    """The case flagged during planning: a.md linking to b.md/b.html
    is a reference to another authored page, never a transclusion, so
    it must not become a build dependency (unlike link_filter itself,
    which doesn't make this distinction -- see issue #23)."""
    assert deps_filter.is_local_asset_url("introduction.md") is False
    assert deps_filter.is_local_asset_url("introduction.html") is False


def test_is_local_asset_url_true_for_a_real_attachment():
    assert deps_filter.is_local_asset_url("handout.pdf") is True


def test_is_local_asset_url_false_for_page_reference_with_a_fragment():
    """Regression: a link to a specific section of another page
    (introduction.md#variables) was misclassified as a real asset --
    the raw url's own "extension" is ".md#variables", not in the
    excluded set, because the fragment was never stripped first."""
    assert deps_filter.is_local_asset_url("introduction.md#variables") is False
    assert deps_filter.is_local_asset_url("introduction.html#variables") is False


def test_is_local_asset_url_true_for_a_real_attachment_with_a_fragment():
    """A genuine asset link can carry a fragment too (e.g. a browser
    PDF viewer's #page=3) -- still a real attachment, extension check
    just needs to ignore the fragment either way."""
    assert deps_filter.is_local_asset_url("handout.pdf#page=3") is True


## collect_deps -- CodeBlock

def test_collect_deps_include_needs_raw_and_tpf_for_html_but_only_raw_for_full():
    elem = pf.CodeBlock("", classes=["python"], attributes={"include": "demo.py"})
    doc = make_doc(elem)

    html_deps, full_deps = deps_filter.collect_deps(doc)

    assert html_deps == ["demo.py", "demo.py.tpf"]
    assert full_deps == ["demo.py"]


def test_collect_deps_output_needs_only_raw_for_both():
    elem = pf.CodeBlock(
        "", classes=["python"],
        attributes={"include": "demo.py", "output": "true"},
    )
    doc = make_doc(elem)

    html_deps, full_deps = deps_filter.collect_deps(doc)

    assert "demo.out" in html_deps
    assert "demo.out" in full_deps
    ## canvas_filter reads .out directly -- no tpf() lookup, unlike
    ## `include` itself.
    assert not any(d.endswith(".out.tpf") for d in html_deps)


## collect_deps -- Image

def test_collect_deps_image_needs_tpf_for_html_and_raw_for_full():
    elem = pf.Image(pf.Str("x"), url="test-image.png")
    doc = make_doc(pf.Para(elem))

    html_deps, full_deps = deps_filter.collect_deps(doc)

    assert html_deps == ["test-image.png.tpf"]
    assert full_deps == ["test-image.png"]


## collect_deps -- Link

def test_collect_deps_link_to_asset_needs_tpf_for_html_and_raw_for_full():
    elem = pf.Link(pf.Str("x"), url="handout.pdf")
    doc = make_doc(pf.Para(elem))

    html_deps, full_deps = deps_filter.collect_deps(doc)

    assert html_deps == ["handout.pdf.tpf"]
    assert full_deps == ["handout.pdf"]


def test_collect_deps_link_to_another_page_is_not_a_dependency():
    elem = pf.Link(pf.Str("x"), url="introduction.html")
    doc = make_doc(pf.Para(elem))

    html_deps, full_deps = deps_filter.collect_deps(doc)

    assert html_deps == []
    assert full_deps == []


def test_collect_deps_external_link_is_not_a_dependency():
    elem = pf.Link(pf.Str("x"), url="https://example.com/foo")
    doc = make_doc(pf.Para(elem))

    html_deps, full_deps = deps_filter.collect_deps(doc)

    assert html_deps == []
    assert full_deps == []


def test_collect_deps_deduplicates_preserving_order():
    elem1 = pf.Image(pf.Str("x"), url="test-image.png")
    elem2 = pf.Image(pf.Str("y"), url="test-image.png")
    doc = make_doc(pf.Para(elem1), pf.Para(elem2))

    html_deps, full_deps = deps_filter.collect_deps(doc)

    assert html_deps == ["test-image.png.tpf"]
    assert full_deps == ["test-image.png"]
