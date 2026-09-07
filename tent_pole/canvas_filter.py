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
    erroring -- replaces GNU source-highlight, whose per-language config
    files were fragile to extend for new/obscure languages."""
    try:
        lexer = pygments.lexers.get_lexer_by_name(lang)
    except pygments.util.ClassNotFound:
        lexer = pygments.lexers.get_lexer_by_name("text")
    formatter = pygments.formatters.HtmlFormatter(noclasses=True)
    return pygments.highlight(text, lexer, formatter)

def code_filter(elem, doc):
    lang = len(elem.classes) > 0  and elem.classes[0]
    include=elem.attributes.get("include")
    output=elem.attributes.get("output")
    stout=elem.attributes.get("stout")
    crash=elem.attributes.get("crash")

    if not include:
        fd, path = tempfile.mkstemp(text=True)
        f = open(path, "w")
        f.write(elem.text)
        f.flush()

    with open(include or path) as fh:
        content = fh.read()

    if lang:
        highlighted = highlight_source(content, lang)
    else:
        highlighted = "<pre><code>" + content + "\n</code></pre>"

    if not include:
        f.close()

    if include:
        include_url = "../files/{}/download".format(str(tpf(include).get("id")))

    if output:
        name = os.path.splitext(include)[0]
        with open(name + ".out" ) as fh: output_text = fh.read()
        fh.close()

    if stout:
        name = os.path.splitext(include)[0]
        with open(name + ".stout" ) as fh: stout_text = fh.read()
        fh.close()

    if crash:
        name = os.path.splitext(include)[0]
        with open(name + ".crash" ) as fh: crash_text = fh.read()
        fh.close()


    return [i for i in
            [
                RawBlock(highlighted),
                include and Para(Link
                                 (Str("Take from: "
                                      + os.path.basename(include)),
                                  url=include_url)),
                output and Para(Str("Outputs:")),
                output and CodeBlock(output_text),
                stout and Para(Str("Prints:")),
                stout and CodeBlock(stout_text),
                crash and Para(Str("Crashes:")),
                crash and CodeBlock(crash_text)
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
  src="https://ncl.instructure.com/media_objects_iframe/{uuid}?type=video"
  allowfullscreen="allowfullscreen" allow="fullscreen"
  data-media-id="{uuid}">
</iframe>
'''.format(uuid=tpf_data.get("media_entry_id")))


    ## Assume it is a file that has to be downloaded, so link to it via the TPF
    include_url = "../files/{}/download".format(str(tpf(elem.url).get("id")))
    elem.url = include_url
    return elem

def image_filter(elem, doc):
    tpf_data = tpf(elem.url)
    return RawInline('''<img id="{id}"
src="https://ncl.instructure.com/courses/{course}/files/{id}/preview"
alt="{name}" />
'''.format(id=tpf_data.get("id"),name=elem.title,
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
    on save (confirmed live against the sandbox course), but preserves a
    plain hidden <span> with a data attribute intact."""
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
