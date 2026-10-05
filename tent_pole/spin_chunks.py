"""Pure text splitter for knitr spin()'s own chunk convention --
`#+ chunk-name` opens a chunk, `#'` marks prose. No parsing of the
language inside a chunk, no execution: this is boundary detection
only, shared by the display-side filters and the R-side build helper
so chunk-boundary semantics live in exactly one place rather than
being re-implemented twice. See r_support_design.md.

A marker can sit at any indentation, not just column 0 -- R's own
chunks are conventionally flat, but Python's aren't: a `def`/`class`
body is indented, and a marker nested inside one is exactly the case
Python chunk support needs (see r_support_design.md's step 11 note).
The returned source is dedented, so a chunk pulled out of a nested
block reads as standalone code rather than carrying its enclosing
indentation along -- a no-op for an already-flat chunk."""

import re
import textwrap

CHUNK_MARKER = re.compile(r"^\s*#\+\s*(.+?)\s*$")
PROSE_MARKER = re.compile(r"^\s*#'")


def split_chunks(source):
    """A chunk runs from its `#+ chunk-name` line until the next
    `#+`, the next `#'`, or end of file -- there is no explicit close
    marker, the same "runs until the next marker" shape as the quiz
    parser's own `##` question headers. Returns an insertion-ordered
    dict[chunk_name, source_text]; prose, and anything before the
    first chunk marker, is dropped rather than represented."""
    chunks = {}
    name = None
    lines = []

    def flush():
        if name is not None:
            chunks[name] = textwrap.dedent("\n".join(lines)).rstrip()

    for line in source.splitlines():
        marker = CHUNK_MARKER.match(line)
        if marker:
            flush()
            name = marker.group(1)
            lines = []
        elif PROSE_MARKER.match(line):
            flush()
            name = None
            lines = []
        elif name is not None:
            lines.append(line)

    flush()
    return chunks
