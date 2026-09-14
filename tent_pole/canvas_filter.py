import datetime
import os
import re
import tempfile
import toml
from urllib.parse import urlparse

import pygments
import pygments.formatters
import pygments.lexers
import pygments.util

from panflute import *

from . import config
from . import quiz_paths
from .code_include_attrs import CodeIncludeAttrs

COMPILED_AT_PATTERN = re.compile(r'data-compiled-at="([^"]*)"')

def tpp(f):
    return toml.load(f + ".tpp")

def tpf(f):
    return toml.load(f + ".tpf")

def extract_compiled_at(html):
    """Reads back the compile timestamp embedded by add_tent_pole_marker,
    if present. None if the content was never processed by canvas-filter
    (e.g. raw HTML pushed directly) -- see that function's docstring."""
    match = COMPILED_AT_PATTERN.search(html)
    return match.group(1) if match else None

def highlight_source(text, lang):
    """Syntax-highlight `text` as `lang` using Pygments, falling back to
    unhighlighted plain text for an unrecognised language rather than
    erroring."""
    try:
        lexer = pygments.lexers.get_lexer_by_name(lang)
    except pygments.util.ClassNotFound:
        lexer = pygments.lexers.get_lexer_by_name("text")
    formatter = pygments.formatters.HtmlFormatter(noclasses=True)
    return pygments.highlight(text, lexer, formatter)

def code_filter(elem, doc):
    lang = len(elem.classes) > 0  and elem.classes[0]
    attrs = CodeIncludeAttrs.from_element(elem)

    if not attrs.include:
        fd, path = tempfile.mkstemp(text=True)
        f = open(path, "w")
        f.write(elem.text)
        f.flush()

    with open(attrs.include or path) as fh:
        content = fh.read()

    if lang:
        highlighted = highlight_source(content, lang)
    else:
        highlighted = "<pre><code>" + content + "\n</code></pre>"

    if not attrs.include:
        f.close()

    if attrs.include:
        include_url = "../files/{}/download".format(str(tpf(attrs.include).get("id")))

    if attrs.output:
        with open(attrs.output_path) as fh: output_text = fh.read()

    if attrs.stout:
        with open(attrs.stout_path) as fh: stout_text = fh.read()

    show_crash = attrs.crash and not attrs.hide_crash
    if show_crash:
        with open(attrs.crash_path) as fh: crash_text = fh.read()

    return [i for i in
            [
                RawBlock(highlighted),
                attrs.include and Para(Link
                                 (Str("Taken from: "
                                      + os.path.basename(attrs.include)),
                                  url=include_url)),
                attrs.output and Para(Str("Outputs:")),
                attrs.output and CodeBlock(output_text),
                attrs.stout and Para(Str("Prints:")),
                attrs.stout and CodeBlock(stout_text),
                show_crash and Para(Str("Crashes:")),
                show_crash and CodeBlock(crash_text)
            ]
            if i
        ]

def link_filter(elem, doc):
    ## Not a local URL so take it as it comes
    parsed = urlparse(elem.url)
    if bool(parsed.netloc) or bool(parsed.scheme):
        return elem

    ## A link to a quiz: checked before the generic page-link branch
    ## below, since os.path.splitext only ever strips the *last*
    ## extension -- "something.quiz.md" still splits to ext ".md",
    ## which would otherwise be caught there first and resolved
    ## against a .tpp that will never exist for a quiz. Confirmed by
    ## reading the real code, not assumed. Resolve directly to the
    ## quiz's own .tpq-recorded html_url -- already absolute, unlike a
    ## page's relative slug, so no further resolution is needed. Any
    ## #fragment is dropped: a quiz has no addressable internal
    ## headings the way a page does. Falls back to the bare local path
    ## (matching the page branch's own behaviour) when the target
    ## hasn't been pushed yet -- like page-to-page links, a
    ## page-to-quiz link is deliberately never a .tpd build dependency.
    path, _, fragment = elem.url.partition("#")
    if path.endswith(".quiz.md"):
        tpq_path = quiz_paths.tpq_path(path)
        elem.url = (
            toml.load(tpq_path).get("html_url", path)
            if os.path.exists(tpq_path) else path
        )
        return elem

    base, ext = os.path.splitext(elem.url)

    ## A link to another Canvas page: either bare (no extension -- the
    ## common authoring form) or spelled out with its .md source or
    ## its locally-rendered .html. Both are a page reference, never a
    ## file attachment -- there is no intro.html.tpf, intro.html was
    ## never pushed via file push, it's a page (tent-pole issue #23).
    ## Resolve to the target's real url if it's been pushed+dumped
    ## already -- its .tpp records pageobj.url (page.py's
    ## __resolve_page-corrected real url), which can differ from the
    ## link text once Canvas has ever reserved that slug for a deleted
    ## page's undelete (tent-pole issue #29). Left as the bare name,
    ## matching previous behaviour, when the target hasn't been dumped
    ## yet -- a page-to-page link is deliberately never a .tpd build
    ## dependency (unlike an image/file link), so there's no ordering
    ## guarantee that it has been.
    if ext in ("", ".md", ".html"):
        ## path/fragment already split off above -- the dumped page is
        ## keyed by its own url alone, never url#fragment, and never
        ## with a .md/.html suffix either.
        page_path = os.path.splitext(path)[0]
        tpp_path = page_path + ".tpp"
        real_url = (
            toml.load(tpp_path).get("url", page_path)
            if os.path.exists(tpp_path) else page_path
        )
        elem.url = real_url + ("#" + fragment if fragment else "")
        return elem

    ## MP4 uses media player
    if ext == ".mp4":
        tpf_data = tpf(elem.url)
        return RawInline('''
<iframe style="width: 400px; height: 225px; display: inline-block;"
  title="Video player"
  data-media-type="video"
  src="{api_url}/media_objects_iframe/{uuid}?type=video"
  allowfullscreen="allowfullscreen" allow="fullscreen"
  data-media-id="{uuid}">
</iframe>
'''.format(api_url=config.config_api_url(), uuid=tpf_data.get("media_entry_id")))


    ## Assume it is a file that has to be downloaded, so link to it via the TPF
    include_url = "../files/{}/download".format(str(tpf(elem.url).get("id")))
    elem.url = include_url
    return elem

def image_filter(elem, doc):
    tpf_data = tpf(elem.url)
    ## Priority: an explicit alt="..." attribute (the ![](url){alt="..."}
    ## form, which also avoids pandoc's implicit-figure/caption promotion
    ## of a standalone image -- see claude_include_replacement.md-adjacent
    ## notes), then the bracket text of ![alt](url), which is stringify()'d
    ## from elem.content, not elem.title -- .title is only the optional
    ## quoted string after the url, e.g. ![alt](url "title"), and was
    ## wrongly used for alt text before this fix, silently producing
    ## alt="" for every image using the plain ![alt](url) form.
    alt = elem.attributes.get("alt") or stringify(elem) or elem.title
    ## width/height come through from the ![](url){width=... height=...}
    ## attribute syntax same as alt -- pass them on verbatim (pandoc
    ## already normalises "400" vs "50%" etc, so no parsing needed here)
    ## rather than silently dropping them as before.
    size_attrs = "".join(
        ' {0}="{1}"'.format(name, elem.attributes[name])
        for name in ("width", "height") if elem.attributes.get(name)
    )
    return RawInline('''<img id="{id}"
src="{api_url}/courses/{course}/files/{id}/preview"
alt="{name}"{size_attrs} />
'''.format(api_url=config.config_api_url(), id=tpf_data.get("id"), name=alt,
           canvas_uri=tpf_data.get("canvas_uri"),
           course=tpf_data.get("course"), size_attrs=size_attrs))


def canvas_filter(elem, doc):
    if type(elem) == Image:
        return image_filter(elem, doc)

    if type(elem) == Link:
        return link_filter(elem, doc)

    if type(elem) == CodeBlock:
        return code_filter(elem, doc)

def add_tent_pole_marker(doc):
    """Appends a hidden marker span carrying a compile timestamp, so a
    page pushed through canvas-filter can be positively identified as
    tent-pole-managed, and the exact build currently live on Canvas can
    be verified later (compare this timestamp against what tent_pole.page
    records at push time) rather than just inferring drift from
    last_edited_by/updated_at. Deliberately not an HTML comment --
    Canvas's sanitizer strips comments from page bodies unconditionally
    on save, but preserves a plain hidden <span> with a data attribute
    intact."""
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    marker = RawBlock(
        '<span style="display:none" data-tent-pole="managed" '
        'data-compiled-at="{}"></span>'.format(timestamp)
    )
    doc.content.append(marker)

def main(doc=None):
    return run_filter(canvas_filter, finalize=add_tent_pole_marker, doc=doc)

if __name__ == '__main__':
    main()
