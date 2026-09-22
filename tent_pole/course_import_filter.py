import functools
import html
import os
import re

import canvasapi.exceptions
from panflute import *

FILE_ID_PATTERN = re.compile(r'/files/(\d+)')
PAGE_SLUG_PATTERN = re.compile(r'/pages/([^/?#]+)(#[^?]*)?')

## GNU source-highlight's own markup, predating tent-pole's switch to
## Pygments (see canvas_filter.highlight_source) -- real courses that
## have been live a while still have plenty of pages built with the
## old highlighter, so this isn't legacy in the sense of rare. Each
## source line is its own <font color="#000000">N:</font>-prefixed
## run inside a single <pre><tt>...</tt></pre>; pandoc's HTML reader
## has no special handling for <tt>/<font>/<b>/<i> the way it does for
## <pre><code>, so left alone this comes out as a wall of nested
## Code/Strong/Emph spans with literal "N: " text, not a code block.
## Stripped back to a plain <pre><code> block here, before pandoc ever
## sees it, so it round-trips through the same already-correct generic
## path as an ordinary code block.
LEGACY_HIGHLIGHT_BLOCK_PATTERN = re.compile(r'<pre><tt>(.*?)</tt></pre>', re.DOTALL)
LEGACY_LINE_NUMBER_PATTERN = re.compile(r'<font[^>]*>\d+:</font> ?', re.MULTILINE)
LEGACY_TAG_PATTERN = re.compile(r'</?(?:font|b|i|u)\b[^>]*>')


def __unwrap_legacy_source_highlight(page_html):
    def unwrap(match):
        inner = LEGACY_LINE_NUMBER_PATTERN.sub("", match.group(1))
        inner = LEGACY_TAG_PATTERN.sub("", inner)
        return "<pre><code>" + inner + "</code></pre>"

    return LEGACY_HIGHLIGHT_BLOCK_PATTERN.sub(unwrap, page_html)


## canvas_filter's own mp4 -> video-player embed (link_filter's ext ==
## ".mp4" branch) renders as an <iframe data-media-id="..." src=".../
## media_objects_iframe/...">, addressing a Canvas *media object*, not
## a regular file -- canvasapi has no media-object download support at
## all (unlike course.get_file() for an ordinary file/image), so unlike
## an include='d source file, there is currently nothing to actually
## fetch here. Left as a plain note rather than silently vanishing:
## by default pandoc's HTML reader drops any tag it doesn't recognise,
## iframe included, with no trace at all -- confirmed empirically, not
## assumed -- so doing nothing here would silently delete real content
## rather than degrading to best-effort.
VIDEO_IFRAME_PATTERN = re.compile(r'<iframe\b([^>]*)>.*?</iframe>', re.DOTALL)
MEDIA_ID_ATTRIBUTE_PATTERN = re.compile(r'data-media-id="([^"]*)"')
TITLE_ATTRIBUTE_PATTERN = re.compile(r'\btitle="([^"]*)"')

## Theme/institution-injected chrome (analytics, mobile-config), not
## authored course content -- stripped the same way the tent-pole
## managed marker span is, rather than surviving as inert raw HTML.
SCRIPT_TAG_PATTERN = re.compile(r'<script\b[^>]*>.*?</script>|<script\b[^>]*/>', re.DOTALL)


def __replace_video_iframes(page_html):
    def replace(match):
        attrs = match.group(1)
        media_id_match = MEDIA_ID_ATTRIBUTE_PATTERN.search(attrs)
        if media_id_match is None:
            return match.group(0)

        title_match = TITLE_ATTRIBUTE_PATTERN.search(attrs)
        label = title_match.group(1) if title_match else media_id_match.group(1)
        print("Warning: video embed {!r} could not be downloaded (no media-object "
              "download support), left as a note instead".format(label))
        return "<p><em>[Video not imported: {}]</em></p>".format(html.escape(label))

    return VIDEO_IFRAME_PATTERN.sub(replace, page_html)


def __strip_script_tags(page_html):
    return SCRIPT_TAG_PATTERN.sub("", page_html)


class ImportContext:
    """Per-run state threaded through import_filter via functools.partial:
    the live course handle, the slugs of the pages being imported this run
    (so an in-course page link can be told apart from one pointing outside
    the import), the directory pages/files are being written into, and a
    download cache so a file referenced from multiple pages is fetched
    once."""

    def __init__(self, courseobj, page_slugs, output_dir):
        self.courseobj = courseobj
        self.page_slugs = set(page_slugs)
        self.output_dir = output_dir
        self.file_cache = {}
        self.used_filenames = set(os.listdir(output_dir))

    def download_file(self, file_id):
        """The local filename an earlier or fresh download landed under,
        or None if Canvas no longer has this file (real-world drift on a
        long-lived course -- a link can outlive the file it pointed at).
        A missing file is reported, not a crash: the link/image referring
        to it is left as-is by the caller rather than losing the whole
        import over one stale reference."""
        if file_id in self.file_cache:
            return self.file_cache[file_id]

        try:
            canvas_file = self.courseobj.get_file(file_id)
            content = canvas_file.get_contents(binary=True)
        except canvasapi.exceptions.CanvasException as e:
            print("Warning: file {} could not be downloaded ({}), leaving its link/image as-is".format(file_id, e))
            self.file_cache[file_id] = None
            return None

        filename = self.__unique_filename(canvas_file.filename)
        with open(os.path.join(self.output_dir, filename), "wb") as fh:
            fh.write(content)

        self.file_cache[file_id] = filename
        return filename

    def __unique_filename(self, filename):
        candidate = filename
        base, ext = os.path.splitext(filename)
        n = 1
        while candidate in self.used_filenames:
            n += 1
            candidate = "{}-{}{}".format(base, n, ext)
        self.used_filenames.add(candidate)
        return candidate


def __is_managed_marker(elem):
    return isinstance(elem, Span) and elem.attributes.get("tent-pole") == "managed"


def __extract_file_id(url):
    match = FILE_ID_PATTERN.search(url)
    return int(match.group(1)) if match else None


def __extract_page_slug(url):
    """(slug, fragment) for a /pages/<slug>[#fragment] URL, or (None, None)
    if the url doesn't look like a page link at all."""
    match = PAGE_SLUG_PATTERN.search(url)
    return (match.group(1), match.group(2) or "") if match else (None, None)


def __pygments_plain_text(elem):
    """Recovers the literal source text from a Pygments noclasses=True
    highlight block -- see tent_pole/course_import_filter's design notes:
    generic pandoc HTML->markdown mangles this into bracketed-span
    syntax, so it needs walking by hand instead, collecting only literal
    text/whitespace nodes and ignoring the style spans wrapping them.
    Pandoc's HTML reader also turns a lone space inside a styled span
    (used by Pygments to keep leading/inline whitespace significant)
    into a literal non-breaking space Str rather than a collapsible
    Space node -- normalised back to a plain space here."""
    parts = []

    def collect(e, doc):
        if isinstance(e, Str):
            parts.append(e.text)
        elif isinstance(e, Space):
            parts.append(" ")
        elif isinstance(e, LineBreak) or isinstance(e, SoftBreak):
            parts.append("\n")

    elem.walk(collect)
    return "".join(parts).replace("\xa0", " ")


## Attributes worth keeping from a hand-authored (Canvas RCE) <img> --
## everything else Canvas/pandoc attaches (the file id as #identifier,
## loading="lazy", data-api-endpoint/-returntype) is editor/API
## bookkeeping, not authoring intent, and would otherwise leak into the
## markdown as {#123 loading="lazy" api-endpoint="..." ...} clutter.
IMAGE_ATTRIBUTES_TO_KEEP = ("width", "height")


def image_filter(elem, context):
    file_id = __extract_file_id(elem.url)
    if file_id is None:
        return None

    local_filename = context.download_file(file_id)
    if local_filename is not None:
        elem.url = local_filename

    elem.identifier = ""
    elem.attributes = {
        k: v for k, v in elem.attributes.items() if k in IMAGE_ATTRIBUTES_TO_KEEP
    }
    return elem


def link_filter(elem, context):
    slug, fragment = __extract_page_slug(elem.url)
    if slug is not None:
        if slug in context.page_slugs:
            elem.url = slug + fragment
        return elem

    file_id = __extract_file_id(elem.url)
    if file_id is not None:
        local_filename = context.download_file(file_id)
        if local_filename is not None:
            elem.url = local_filename
        return elem

    return elem


## The only language include=/output=/stout=/crash= currently supports
## (tent_pole/docs/include-code.md: "This is currently Python-specific").
## Recovering the language from the downloaded include file's own
## extension, rather than the rendered code block, since a Pygments
## noclasses=True block carries no language name anywhere in its
## output -- only colours.
LANGUAGE_BY_EXTENSION = {".py": "python"}


def __taken_from_link_target(elem):
    """The link's url if elem is exactly the Para(Link(...)) that
    code_filter emits right after an include='d code block ("Taken
    from: <file>"), else None."""
    if not (isinstance(elem, Para) and len(elem.content) == 1
            and isinstance(elem.content[0], Link)):
        return None
    link = elem.content[0]
    return link.url if stringify(link).startswith("Taken from: ") else None


def __section_label(elem, label):
    return (isinstance(elem, Para) and len(elem.content) == 1
            and isinstance(elem.content[0], Str) and elem.content[0].text == label)


def __fold_code_includes(items, context):
    """A code_filter-produced [highlighted code][Taken from: <file>
    link][Outputs:/Prints:/Crashes: sections] run of blocks -> a single
    `{include=<file> ...}` CodeBlock, so re-running `make pages` against
    the downloaded source regenerates the same rendering instead of the
    reconstructed markdown carrying a frozen, unmaintainable copy of it.
    Only folds when the referenced file actually downloaded -- a broken
    reference (see ImportContext.download_file) is left as a literal
    code block plus its now-inert link, same as any other file/image
    download failure elsewhere in this filter."""
    result = []
    i = 0
    while i < len(items):
        item = items[i]
        target = (
            __taken_from_link_target(items[i + 1])
            if isinstance(item, CodeBlock) and i + 1 < len(items) else None
        )
        if target is None or not os.path.exists(os.path.join(context.output_dir, target)):
            result.append(item)
            i += 1
            continue

        j = i + 2
        directive_attrs = {"include": target}
        for label, attr in (("Outputs:", "output"), ("Prints:", "stout"), ("Crashes:", "crash")):
            if (j + 1 < len(items) and __section_label(items[j], label)
                    and isinstance(items[j + 1], CodeBlock)):
                directive_attrs[attr] = "true"
                j += 2

        lang = LANGUAGE_BY_EXTENSION.get(os.path.splitext(target)[1])
        result.append(CodeBlock("", classes=[lang] if lang else [], attributes=directive_attrs))
        i = j

    return result


def import_filter(elem, doc, context):
    if isinstance(elem, Para) and len(elem.content) == 1 and __is_managed_marker(elem.content[0]):
        return []

    if isinstance(elem, Image):
        return image_filter(elem, context)

    if isinstance(elem, Link):
        return link_filter(elem, context)

    if isinstance(elem, Div) and "highlight" in elem.classes:
        return CodeBlock(__pygments_plain_text(elem))

    return None


def convert(page_html, context):
    """A Canvas page body -> best-effort markdown, in-process (not a
    `pandoc --filter=` subprocess, unlike canvas_filter's forward
    direction) -- context carries a live course handle and a download
    cache that can't cross a subprocess boundary, so the HTML is parsed
    to a panflute Doc, walked with import_filter bound to this run's
    context, and converted back to markdown, all within this process."""
    page_html = __unwrap_legacy_source_highlight(page_html)
    page_html = __replace_video_iframes(page_html)
    page_html = __strip_script_tags(page_html)
    ## +raw_html: without it, pandoc's HTML reader silently discards any
    ## tag it doesn't itself recognise (confirmed empirically) -- a
    ## strictly safer default than losing content with no trace, for
    ## whatever Canvas/editor cruft isn't specifically handled above.
    doc = convert_text(page_html, input_format="html+raw_html", output_format="panflute", standalone=True)
    action = functools.partial(import_filter, context=context)
    doc = run_filters([action], doc=doc)
    doc.content = __fold_code_includes(list(doc.content), context)
    return convert_text(doc, input_format="panflute", output_format="markdown")
