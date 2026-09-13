import os

QUIZ_MD_SUFFIX = ".quiz.md"


def tpq_path(filename):
    """The .tpq stamp-file path for a .quiz.md source. ".quiz.md" is
    treated as one compound extension throughout, not
    os.path.splitext's single-extension stripping -- this matches the
    Make pattern rule `%.tpq: %.quiz.md`, where Make's own % captures
    everything before the literal ".quiz.md" suffix. Shared between
    quiz.py and canvas_filter.py (which can't import each other
    directly -- canvas_filter -> quiz -> quiz_parser -> canvas_filter
    would be circular) so the two never drift apart, the same reason
    CodeIncludeAttrs lives in its own module rather than in
    canvas_filter.py itself."""
    if filename.endswith(QUIZ_MD_SUFFIX):
        return filename[: -len(QUIZ_MD_SUFFIX)] + ".tpq"
    return os.path.splitext(filename)[0] + ".tpq"
