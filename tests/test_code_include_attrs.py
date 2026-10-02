"""Offline, no-pandoc unit tests for CodeIncludeAttrs -- chunk=/plot=
parsing and the chunk-aware path properties. No runtime/build change
is exercised here, only the dataclass itself."""

from tent_pole.code_include_attrs import CodeIncludeAttrs


class _FakeElem:
    def __init__(self, **attributes):
        self.attributes = attributes


def _attrs(**kw):
    return CodeIncludeAttrs.from_element(_FakeElem(**kw))


def test_chunk_and_plot_default_to_none():
    attrs = _attrs(include="demo.py")

    assert attrs.chunk is None
    assert attrs.plot is None


def test_plot_true_means_figure_one():
    attrs = _attrs(include="demo.R", plot="true")

    assert attrs.plot == 1


def test_plot_number_is_parsed_as_int():
    attrs = _attrs(include="demo.R", plot="2")

    assert attrs.plot == 2


def test_plot_false_is_the_same_as_absent():
    attrs = _attrs(include="demo.R", plot="false")

    assert attrs.plot is None


def test_chunk_is_passed_through_verbatim():
    attrs = _attrs(include="demo.R", chunk="setup")

    assert attrs.chunk == "setup"


def test_paths_fall_back_to_whole_file_naming_without_a_chunk():
    attrs = _attrs(include="demo.py", output="true", stout="true", crash="true")

    assert attrs.output_path == "demo.out"
    assert attrs.stout_path == "demo.stout"
    assert attrs.crash_path == "demo.crash"
    assert attrs.referenced_paths() == [
        "demo.py", "demo.out", "demo.stout", "demo.crash",
    ]


def test_paths_are_chunk_aware_when_chunk_is_set():
    attrs = _attrs(
        include="demo.R", chunk="summary-stats", output="true", stout="true",
        crash="true",
    )

    assert attrs.output_path == "demo_summary-stats.out"
    assert attrs.stout_path == "demo_summary-stats.stout"
    assert attrs.crash_path == "demo_summary-stats.crash"


def test_plot_path_is_chunk_aware_and_numbered():
    attrs = _attrs(include="demo.R", chunk="make-plot", plot="2")

    assert attrs.plot_path == "demo_make-plot-2.png"


def test_referenced_paths_includes_the_plot_path_when_set():
    attrs = _attrs(include="demo.R", chunk="make-plot", plot="true")

    assert attrs.referenced_paths() == [
        "demo.R", "demo_make-plot-1.png",
    ]
