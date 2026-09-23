"""Offline, no-network tests for the doit task-creators in
tent_pole/doit_rules -- asserting directly on the yielded task dicts
(names, file_dep, targets, actions), the same spirit as
test_bin_generate_makefile.py testing generated Makefile text without
ever running `make`. Needs real pandoc (like the existing
include_deps_filter pandoc-integration tests) since task_html/
task_full_html/task_tpf call through to it via include_deps_filter.parse.
"""

import os
import shutil
import subprocess
import sys

import pytest

from tent_pole import doit_rules
from tent_pole.doit_rules import core

PANDOC = shutil.which("pandoc")
pytestmark = pytest.mark.skipif(PANDOC is None, reason="pandoc not installed")


def test_tent_pole_falls_back_to_sys_argv0():
    """If TENT_POLE isn't set, task actions must call back into
    whichever binary actually launched this process (sys.argv[0]), not
    a hardcoded "tent-pole" -- otherwise e.g. `tent-pole-next build`
    would silently push through a different installed tent-pole for
    every internal fan-out/page-push/module-create action. Run in a
    fresh subprocess since TENT_POLE is frozen at module-import time,
    which already happened for this test file's own `core` import."""
    env = dict(os.environ)
    env.pop("TENT_POLE", None)
    result = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.argv[0] = '/opt/bin/tent-pole-custom'\n"
         "from tent_pole.doit_rules import core\n"
         "print(core.TENT_POLE)"],
        capture_output=True, text=True, check=True, env=env,
    )
    assert result.stdout.strip() == "/opt/bin/tent-pole-custom"


def _write(path, content):
    path.write_text(content)


@pytest.fixture
def course_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_task_html_one_subtask_per_non_quiz_md(course_dir):
    _write(course_dir / "foo.md", "hello\n")
    _write(course_dir / "bar.quiz.md", "hello\n")

    tasks = {t["name"]: t for t in core.task_html()}

    assert list(tasks) == ["foo.html"]
    task = tasks["foo.html"]
    assert task["targets"] == ["foo.html"]
    assert "foo.md" in task["file_dep"]
    assert task["actions"] == [["pandoc", "--filter=canvas-filter", "foo.md", "-o", "foo.html"]]


def test_task_full_html_excludes_quiz_md(course_dir):
    _write(course_dir / "foo.md", "hello\n")
    _write(course_dir / "bar.quiz.md", "hello\n")

    names = [t["name"] for t in core.task_full_html()]

    assert names == ["foo.full.html"]


def test_task_quiz_full_covers_only_quiz_md(course_dir):
    _write(course_dir / "foo.md", "hello\n")
    _write(course_dir / "bar.quiz.md", "hello\n")

    names = [t["name"] for t in core.task_quiz_full()]

    assert names == ["bar.quiz.full.html"]


def test_task_page_push_depends_on_html_not_md(course_dir):
    _write(course_dir / "foo.md", "hello\n")

    (task,) = list(core.task_page_push())

    assert task["name"] == "foo.tpp"
    assert task["targets"] == ["foo.tpp"]
    assert task["file_dep"] == ["foo.html"]
    assert task["actions"] == [
        [core.TENT_POLE, "page", "push", "foo.html"],
        [core.TENT_POLE, "page", "dump", "foo.html"],
    ]


def test_task_quiz_push_needs_no_separate_dump(course_dir):
    _write(course_dir / "bar.quiz.md", "hello\n")

    (task,) = list(core.task_quiz_push())

    assert task["name"] == "bar.tpq"
    assert task["actions"] == [[core.TENT_POLE, "quiz", "push", "bar.quiz.md"]]


def test_task_tpf_discovers_embedded_image(course_dir):
    _write(course_dir / "foo.md", "![a diagram](diagram.png)\n")

    (task,) = list(core.task_tpf())

    assert task["name"] == "diagram.png"
    assert task["targets"] == ["diagram.png.tpf"]
    assert task["file_dep"] == ["diagram.png"]


def test_task_tpf_mp4_gets_wait_on_dump(course_dir):
    _write(course_dir / "foo.md", "[video](clip.mp4)\n")

    (task,) = list(core.task_tpf())

    dump_action = task["actions"][1]
    assert dump_action == [core.TENT_POLE, "file", "dump", "--wait", "clip.mp4"]


def test_task_tpf_dedupes_a_file_referenced_from_two_pages(course_dir):
    _write(course_dir / "foo.md", "![a](shared.png)\n")
    _write(course_dir / "bar.md", "![b](shared.png)\n")

    tasks = list(core.task_tpf())

    assert len(tasks) == 1


def test_task_reorder_absent_without_toml(course_dir):
    assert list(core.task_reorder()) == []


def test_task_reorder_present_with_toml(course_dir):
    _write(course_dir / "tent-pole.toml", "[module]\n")

    (task,) = list(core.task_reorder())

    assert task["targets"] == ["tent-pole.toml.tpm"]
    assert task["file_dep"] == ["tent-pole.toml"]


def test_fan_out_yields_one_subtask_per_child_with_no_freshness_check(course_dir):
    """The one property the whole recursive-dispatch design depends
    on: a fan-out subtask has neither file_dep/targets nor an
    uptodate, so doit always treats it as stale and always dispatches
    -- see claude-make-replacement.md."""
    (course_dir / "week-1").mkdir()
    (course_dir / "week-1" / "tent-pole.toml").write_text("[module]\n")
    (course_dir / "week-2").mkdir()
    (course_dir / "week-2" / "tent-pole.toml").write_text("[module]\n")
    (course_dir / "not-a-module").mkdir()

    tasks = {t["name"]: t for t in doit_rules._fan_out("pages")}

    assert set(tasks) == {"week-1", "week-2"}
    for task in tasks.values():
        assert "file_dep" not in task
        assert "targets" not in task
        assert "uptodate" not in task


def test_run_subprocess_returns_a_doit_compatible_value():
    """Regression: subprocess.run's own CompletedProcess satisfies none
    of doit's accepted python-action return types (False/True/None/str/
    dict), so using it directly as an action callable crashed with
    "Python Task error" even when the subprocess itself had already
    succeeded -- found live running a real fan-out for the first time,
    not caught by shape-only assertions on the yielded task dict."""
    assert doit_rules.run_subprocess(["true"]) is True


def test_task_pages_combines_own_pages_and_fan_out(course_dir):
    _write(course_dir / "foo.md", "hello\n")
    (course_dir / "child").mkdir()
    (course_dir / "child" / "tent-pole.toml").write_text("[module]\n")

    names = {t["name"] for t in doit_rules.task_pages()}

    assert names == {"foo.tpp", "child"}
