"""Offline tests for the doit port of bin/generate_makefile.py --
especially that dodo.py itself is never swept up as demo content, the
exact risk this module exists to rule out."""

import pytest

from tent_pole.doit_rules import generate_makefile as gm


@pytest.fixture
def course_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _write(path, content=""):
    path.write_text(content)


def test_dodo_py_is_never_a_candidate(course_dir):
    _write(course_dir / "dodo.py", "from tent_pole.doit_rules import *\n")
    _write(course_dir / "demo.py", "print('hi')\n")

    names = [t["name"] for t in gm.task_generated()]

    assert names == ["demo.out"]


def test_test_prefixed_stem_gets_test_out(course_dir):
    _write(course_dir / "test_stats.py", "def test_x(): assert True\n")

    (task,) = list(gm.task_generated())

    assert task["name"] == "test_stats.test_out"


def test_status_crash_marker_gets_crash(course_dir):
    _write(course_dir / "broken.py", "## Status: Crash\nraise SystemExit(1)\n")

    (task,) = list(gm.task_generated())

    assert task["name"] == "broken.crash"


def test_status_shell_marker_gets_stout(course_dir):
    _write(course_dir / "repl.py", "## Status: Shell\nx = 1\n")

    (task,) = list(gm.task_generated())

    assert task["name"] == "repl.stout"


def test_plain_script_gets_out(course_dir):
    _write(course_dir / "plain.py", "print('hi')\n")

    (task,) = list(gm.task_generated())

    assert task["name"] == "plain.out"


def test_pys_file_gets_stout(course_dir):
    _write(course_dir / "transcript.pys", "1 + 1\n")

    names = [t["name"] for t in gm.task_generated()]

    assert names == ["transcript.stout"]
