"""Pure text splitter for knitr spin()'s own chunk convention --
`#+ chunk-name` opens a chunk, `#'` marks prose. No parsing of the
language inside a chunk, no execution: this is boundary detection
only, shared by the display-side filters and the R-side build helper
so chunk-boundary semantics live in exactly one place rather than
being re-implemented twice. See r_support_design.md."""

import re

CHUNK_MARKER = re.compile(r"^#\+\s*(.+?)\s*$")
PROSE_MARKER = "#'"


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
            chunks[name] = "\n".join(lines).rstrip()

    for line in source.splitlines():
        marker = CHUNK_MARKER.match(line)
        if marker:
            flush()
            name = marker.group(1)
            lines = []
        elif line.startswith(PROSE_MARKER):
            flush()
            name = None
            lines = []
        elif name is not None:
            lines.append(line)

    flush()
    return chunks
