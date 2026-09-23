import io
import os
import subprocess
import sys
from urllib.parse import urlparse

from panflute import CodeBlock, Image, Link, load

from .code_include_attrs import CodeIncludeAttrs

## Not a real pandoc --filter=: this walks the AST purely to collect
## file paths, never transforms the document, and needs no part of the
## stdin/stdout JSON-filter protocol -- routing it through run_filter
## would mean writing the collected dependency list somewhere other
## than stdout, since stdout has to stay valid, unmodified pandoc JSON
## for the protocol to work at all. Simpler to just parse the document
## directly (via `pandoc -t json`, the same thing pandoc itself would
## pipe into a real filter) and print the result.


def is_local_asset_url(url):
    """True for a link to a genuine local asset (a pdf, image, archive,
    etc, meant to be attached/downloaded) -- mirrors canvas_filter's
    own link_filter checks (external URL or no extension -> not a
    local asset), plus excluding .md/.html: a link to another authored
    page is a reference, never a transclusion, so it's not a build
    dependency at all, regardless of extension. See issue #23 -- the
    live link_filter doesn't make this same distinction (yet).

    Extension is checked against parsed.path, not the raw url: a link
    to a specific section of another page (introduction.md#variables)
    is exactly the same kind of reference, but checking the raw url's
    own "extension" would see ".md#variables" -- not in the excluded
    set -- and misclassify it as a real attachment to push."""
    parsed = urlparse(url)
    if parsed.netloc or parsed.scheme:
        return False
    _, ext = os.path.splitext(parsed.path)
    return ext not in ("", ".md", ".html")


def collect_deps(doc):
    """(html_deps, full_deps): the files %.html (canvas-filter) and
    %.full.html (code-include-filter/pandoc) respectively need to
    already exist to build this document. Mirrors what each real
    filter actually reads for each element type -- see the plan for
    the full table this is built from."""
    html_deps = []
    full_deps = []

    def visit(elem, doc):
        if isinstance(elem, CodeBlock):
            attrs = CodeIncludeAttrs.from_element(elem)
            if attrs.include:
                ## code_filter reads the raw file (for highlighting)
                ## *and* looks up its .tpf (for the "Taken from:" link).
                ## code_include_filter only ever reads the raw file.
                html_deps.append(attrs.include)
                html_deps.append(attrs.include + ".tpf")
                full_deps.append(attrs.include)
            ## Guarded, not a tuple-of-(flag, property) loop -- tuple
            ## construction isn't lazy, so evaluating e.g. .output_path
            ## unconditionally crashes on a plain CodeBlock with no
            ## include= at all (attrs.stem needs attrs.include).
            if attrs.output:
                html_deps.append(attrs.output_path)
                full_deps.append(attrs.output_path)
            if attrs.stout:
                html_deps.append(attrs.stout_path)
                full_deps.append(attrs.stout_path)
            if attrs.crash:
                html_deps.append(attrs.crash_path)
                full_deps.append(attrs.crash_path)
        elif isinstance(elem, Image):
            ## image_filter calls tpf(elem.url) unconditionally, never
            ## reads the raw file. pandoc's own --self-contained (the
            ## %.full.html path) embeds the raw file directly.
            html_deps.append(elem.url + ".tpf")
            full_deps.append(elem.url)
        elif isinstance(elem, Link) and is_local_asset_url(elem.url):
            html_deps.append(elem.url + ".tpf")
            full_deps.append(elem.url)
        return elem

    doc.walk(visit)
    ## De-duplicate, preserving order -- a file referenced twice (e.g.
    ## the same image linked and embedded) shouldn't appear twice in
    ## the generated prerequisite list.
    return list(dict.fromkeys(html_deps)), list(dict.fromkeys(full_deps))


def parse(source):
    """(html_deps, full_deps) for `source` -- runs pandoc, parses the
    resulting AST, and returns collect_deps()'s own lists directly.
    Shared by generate() (the Makefile-text tool) and the doit rules
    (tent_pole/doit_rules), which want the lists themselves rather than
    a rendered dependency line."""
    result = subprocess.run(
        ["pandoc", "-t", "json", source],
        capture_output=True, check=True, text=True,
    )
    doc = load(io.StringIO(result.stdout))
    return collect_deps(doc)


def generate(source):
    """The two Makefile dependency lines for `source`, using its own
    concrete stem -- never the literal pattern % -- since Make doesn't
    merge prerequisites across two separate declarations of the same
    pattern rule (verified directly; see the plan)."""
    html_deps, full_deps = parse(source)

    ## Deliberately NOT "%.tpd" as a co-target here, unlike the GNU
    ## manual's own %.o %.d: %.c %.h idiom -- that trick exists because
    ## a header can transitively #include others, so *what* .d lists
    ## can depend on a header's own content. collect_deps() only ever
    ## parses source's own markdown syntax, never any referenced
    ## file's content, so nothing but source itself (already the
    ## pattern rule's own prerequisite) can ever change what .tpd
    ## should say. Making .tpd a co-target of e.g. a .tpf here would
    ## force `make full` (no Canvas access wanted) to push files to
    ## Canvas just to regenerate a dependency-listing file -- confirmed
    ## the hard way running this for real against dev/sample-course.
    stem = os.path.splitext(os.path.basename(source))[0]
    html_line = "{stem}.html: {source} {deps}".format(
        stem=stem, source=source, deps=" ".join(html_deps)
    ).rstrip()
    full_line = "{stem}.full.html: {source} {deps}".format(
        stem=stem, source=source, deps=" ".join(full_deps)
    ).rstrip()
    return html_line, full_line


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    (source,) = argv
    for line in generate(source):
        print(line)


if __name__ == "__main__":
    main()
