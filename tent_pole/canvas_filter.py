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

    if attrs.crash:
        with open(attrs.crash_path) as fh: crash_text = fh.read()

    return [i for i in
            [
                RawBlock(highlighted),
                attrs.include and Para(Link
                                 (Str("Take from: "
                                      + os.path.basename(attrs.include)),
                                  url=include_url)),
                attrs.output and Para(Str("Outputs:")),
                attrs.output and CodeBlock(output_text),
                attrs.stout and Para(Str("Prints:")),
                attrs.stout and CodeBlock(stout_text),
                attrs.crash and Para(Str("Crashes:")),
                attrs.crash and CodeBlock(crash_text)
            ]
            if i
        ]

def link_filter(elem, doc):
    ## Not a local URL so take it as it comes
    parsed = urlparse(elem.url)
    if bool(parsed.netloc) or bool(parsed.scheme):
        return elem

    base, ext = os.path.splitext(elem.url)

    ## If there is no extension, assume this is a local link, so take
    ## it as it comes.
    if ext == "":
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
    return RawInline('''<img id="{id}"
src="{api_url}/courses/{course}/files/{id}/preview"
alt="{name}" />
'''.format(api_url=config.config_api_url(), id=tpf_data.get("id"), name=alt,
           canvas_uri=tpf_data.get("canvas_uri"),
           course=tpf_data.get("course")))


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
