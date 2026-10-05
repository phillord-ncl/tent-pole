"""Offline tests for tent_pole/spin_chunks.py -- pure text splitting,
no R, no execution."""

import os

from tent_pole.spin_chunks import split_chunks

DEMO_R = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dev", "sample-course-r", "demo.R",
)


def test_splits_demo_r_into_its_five_chunks_in_order():
    with open(DEMO_R) as fh:
        chunks = split_chunks(fh.read())

    assert list(chunks) == [
        "setup",
        "summary-stats",
        "make-plot",
        "distribution-plot",
        "standalone-crash",
    ]
    assert chunks["setup"] == "data <- c(4, 8, 15, 16, 23, 42)"
    assert chunks["standalone-crash"] == '"5" / 2'


def test_summary_stats_chunk_keeps_both_lines_in_order():
    with open(DEMO_R) as fh:
        chunks = split_chunks(fh.read())

    assert chunks["summary-stats"] == (
        'cat("Mean:", mean(data), "\\n")\n'
        'cat("SD:", round(sd(data), 2), "\\n")'
    )


def test_prose_before_the_first_chunk_is_dropped():
    source = "#' An intro paragraph.\n#' More prose.\n#+ a\nx <- 1\n"

    assert split_chunks(source) == {"a": "x <- 1"}


def test_trailing_prose_with_nothing_after_it_closes_the_chunk():
    source = "#+ a\nx <- 1\n#' Some closing remarks.\n"

    assert split_chunks(source) == {"a": "x <- 1"}


def test_a_chunk_with_no_code_is_still_recorded_empty():
    source = "#+ empty\n#+ b\ny <- 2\n"

    assert split_chunks(source) == {"empty": "", "b": "y <- 2"}


def test_blank_lines_between_a_chunk_and_the_next_marker_are_trimmed():
    source = "#+ a\nx <- 1\n\n\n#' prose\n"

    assert split_chunks(source) == {"a": "x <- 1"}


def test_a_marker_nested_inside_a_function_body_is_recognised():
    """The case Python needs that R never has: a #+ marker indented
    inside a def/class body, not at column 0."""
    source = (
        "def foo():\n"
        "    #+ inner\n"
        "    x = 1\n"
        "    if x:\n"
        "        y = 2\n"
    )

    assert split_chunks(source) == {"inner": "x = 1\nif x:\n    y = 2"}


def test_a_nested_chunk_is_dedented_but_keeps_its_own_relative_indent():
    """Dedenting strips only the indentation contributed by the
    enclosing block, not indentation genuinely part of the chunk's own
    code (the `if` body above/`y = 2` here stays indented one level
    relative to the `if` line)."""
    source = (
        "class Foo:\n"
        "    def bar(self):\n"
        "        #+ body\n"
        "        for i in range(3):\n"
        "            print(i)\n"
    )

    assert split_chunks(source) == {
        "body": "for i in range(3):\n    print(i)",
    }


def test_a_prose_marker_nested_inside_a_function_body_closes_the_chunk():
    source = (
        "def foo():\n"
        "    #+ a\n"
        "    x = 1\n"
        "    #' an explanation\n"
        "    #+ b\n"
        "    y = 2\n"
    )

    assert split_chunks(source) == {"a": "x = 1", "b": "y = 2"}
