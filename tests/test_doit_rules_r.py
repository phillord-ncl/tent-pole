"""Offline, no-R tests for tent_pole/doit_rules/r.py's task-creator --
asserting directly on the yielded task dicts, the same spirit as
test_doit_rules_python.py. Needs real pandoc since discovery parses
each page via pandoc -t json, the same as include_deps_filter.parse."""

import shutil

import pytest

from tent_pole.doit_rules import r as r_rules

PANDOC = shutil.which("pandoc")
pytestmark = pytest.mark.skipif(PANDOC is None, reason="pandoc not installed")


def _write(path, content):
    path.write_text(content)


@pytest.fixture
def course_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_task_r_groups_output_and_plot_under_one_task(course_dir):
    _write(
        course_dir / "page.md",
        "```{.r include=demo.R chunk=summary-stats output=true}\n```\n\n"
        "```{.r include=demo.R chunk=make-plot plot=true}\n```\n",
    )

    (task,) = list(r_rules.task_r())

    assert task["name"] == "demo.R"
    assert task["file_dep"] == ["demo.R"]
    assert task["targets"] == [
        "demo_summary-stats.out", "demo_make-plot-1.png",
    ]


def test_task_r_skips_a_plain_include_with_no_derived_artifact(course_dir):
    _write(course_dir / "page.md", "```{.r include=demo.R chunk=setup}\n```\n")

    assert list(r_rules.task_r()) == []


def test_task_r_deduplicates_a_target_requested_from_two_pages(course_dir):
    _write(
        course_dir / "page1.md",
        "```{.r include=demo.R chunk=summary-stats output=true}\n```\n",
    )
    _write(
        course_dir / "page2.md",
        "```{.r include=demo.R chunk=summary-stats output=true}\n```\n",
    )

    (task,) = list(r_rules.task_r())

    assert task["targets"] == ["demo_summary-stats.out"]


def test_task_r_does_not_claim_a_target_belonging_to_a_different_py_file(course_dir):
    """The whole reason discovery here can't reuse python.py's
    _referenced(suffix) shape: demo_summary-stats.out can't be
    reversed back to demo.R by string-splitting -- walking each
    CodeBlock's own attrs.include directly sidesteps the ambiguity
    entirely, rather than needing a source-exists filter the way
    doit_rules/python.py did."""
    _write(
        course_dir / "page.md",
        "```{.python include=demo.py output=true}\n```\n",
    )

    assert list(r_rules.task_r()) == []
