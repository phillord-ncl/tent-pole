"""Offline, no-network tests for tent_pole/doit_rules/python.py's
task-creators -- asserting directly on the yielded task dicts, the
same spirit as test_doit_rules.py for core.py. Needs real pandoc since
_referenced discovery calls through to it via include_deps_filter.parse.
"""

import shutil

import pytest

from tent_pole.doit_rules import python as python_rules

PANDOC = shutil.which("pandoc")
pytestmark = pytest.mark.skipif(PANDOC is None, reason="pandoc not installed")


def _write(path, content):
    path.write_text(content)


@pytest.fixture
def course_dir(tmp_path, monkeypatch):
    ## A subdirectory of tmp_path, not tmp_path itself, so a
    ## "../python/..." include= path (see the directory-path test
    ## below) still resolves inside tmp_path rather than escaping it.
    course = tmp_path / "course"
    course.mkdir()
    monkeypatch.chdir(course)
    return course


def test_task_out_discovers_output_true_reference(course_dir):
    _write(course_dir / "demo.py", "")
    _write(course_dir / "page.md", "```{.python include=demo.py output=true}\n```\n")

    (task,) = list(python_rules.task_out())

    assert task["name"] == "demo.out"
    assert task["file_dep"] == ["demo.py"]
    assert task["targets"] == ["demo.out"]


def test_task_out_skips_a_target_whose_py_stem_does_not_exist(course_dir):
    """Regression: task_out's own discovery (_referenced) matches any
    .out reference regardless of which language's include= produced
    it -- a page doing `.R include=plot.R output=true` also shows up
    here. Without the source-file-exists check, python.py would
    wrongly claim plot.out and try to run a nonexistent plot.py."""
    _write(course_dir / "plot.R", "")
    _write(course_dir / "page.md", "```{.r include=plot.R output=true}\n```\n")

    assert list(python_rules.task_out()) == []


def test_task_crash_discovers_crash_true_reference(course_dir):
    _write(course_dir / "broken.py", "")
    _write(course_dir / "page.md", "```{.python include=broken.py crash=true}\n```\n")

    (task,) = list(python_rules.task_crash())

    assert task["name"] == "broken.crash"
    assert task["file_dep"] == ["broken.py"]


def test_task_stout_discovers_stout_true_reference(course_dir):
    _write(course_dir / "repl.py", "")
    _write(course_dir / "page.md", "```{.python include=repl.py stout=true}\n```\n")

    (task,) = list(python_rules.task_stout())

    assert task["name"] == "repl.stout"
    assert task["file_dep"] == ["repl.py"]


def test_task_test_out_discovers_plain_include_of_the_derived_file(course_dir):
    """Regression: unlike .out/.crash/.stout, a page never sets an
    attribute asking for a .test_out -- there's no "test=true"
    CodeIncludeAttrs flag -- it's always a plain include= directly on
    the already-derived .test_out file itself. Found live: a page
    doing `include=python/test_stats.test_out` had nothing building
    that file at all, since task_test_out didn't exist yet."""
    _write(course_dir / "test_stats.py", "")
    _write(course_dir / "page.md", "```{include=test_stats.test_out}\n```\n")

    (task,) = list(python_rules.task_test_out())

    assert task["name"] == "test_stats.test_out"
    assert task["file_dep"] == ["test_stats.py"]
    assert task["targets"] == ["test_stats.test_out"]


def test_task_test_out_recovers_the_py_stem_from_a_directory_path(course_dir):
    (course_dir.parent / "python").mkdir()
    _write(course_dir.parent / "python" / "test_stats.py", "")
    _write(
        course_dir / "page.md",
        "```{include=../python/test_stats.test_out}\n```\n",
    )

    (task,) = list(python_rules.task_test_out())

    assert task["file_dep"] == ["../python/test_stats.py"]
