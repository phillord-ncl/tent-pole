import functools
import os
import re

from panflute import *

FILE_ID_PATTERN = re.compile(r'/files/(\d+)')
PAGE_SLUG_PATTERN = re.compile(r'/pages/([^/?#]+)(#[^?]*)?')


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
        if file_id in self.file_cache:
            return self.file_cache[file_id]

        canvas_file = self.courseobj.get_file(file_id)
        filename = self.__unique_filename(canvas_file.filename)
        with open(os.path.join(self.output_dir, filename), "wb") as fh:
            fh.write(canvas_file.get_contents(binary=True))

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


def image_filter(elem, context):
    file_id = __extract_file_id(elem.url)
    if file_id is None:
        return None

    local_filename = context.download_file(file_id)
    elem.url = local_filename
    return elem


def link_filter(elem, context):
    slug, fragment = __extract_page_slug(elem.url)
    if slug is not None:
        if slug in context.page_slugs:
            elem.url = slug + fragment
        return elem

    file_id = __extract_file_id(elem.url)
    if file_id is not None:
        elem.url = context.download_file(file_id)
        return elem

    return elem


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


def convert(html, context):
    """A Canvas page body -> best-effort markdown, in-process (not a
    `pandoc --filter=` subprocess, unlike canvas_filter's forward
    direction) -- context carries a live course handle and a download
    cache that can't cross a subprocess boundary, so the HTML is parsed
    to a panflute Doc, walked with import_filter bound to this run's
    context, and converted back to markdown, all within this process."""
    doc = convert_text(html, input_format="html", output_format="panflute", standalone=True)
    action = functools.partial(import_filter, context=context)
    doc = run_filters([action], doc=doc)
    return convert_text(doc, input_format="panflute", output_format="markdown")
