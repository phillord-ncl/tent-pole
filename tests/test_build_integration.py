"""Real doit, no network -- the centerpiece test from
claude-make-replacement.md's testing plan. Runs tent_pole.build.run_build
against a temp copy of dev/sample-course, restricted to its Canvas-free
`full`/`quiz_full` targets (no credentials needed, per the sample
course's own README), and checks the properties the whole doit-backend
design has been reasoning about: the right output comes out, an
unchanged rebuild does nothing, and touching one file rebuilds only
that file's task -- plus that a course's own dodo.py (test-image.png/
test-video.mp4 here) is picked up at all, the extensibility case this
design exists to preserve.
"""

import os
import shutil

import pytest

from tent_pole.build import run_build

PANDOC = shutil.which("pandoc")
FFMPEG = shutil.which("ffmpeg")
pytestmark = pytest.mark.skipif(
    PANDOC is None or FFMPEG is None, reason="pandoc/ffmpeg not installed"
)

SAMPLE_COURSE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dev", "sample-course",
)


@pytest.fixture
def sample_course(tmp_path, monkeypatch):
    dest = tmp_path / "sample-course"
    shutil.copytree(SAMPLE_COURSE, dest)
    monkeypatch.chdir(dest)
    return dest


def test_full_build_produces_expected_outputs(sample_course):
    assert run_build(["full"]) == 0

    assert (sample_course / "markdown-features-1.full.html").exists()
    assert (sample_course / "markdown-features-2.full.html").exists()
    ## The course's own dodo.py rules (not tent-pole's built-ins) --
    ## proves a local dodo.py is actually picked up and its extra
    ## rules run alongside the built-in ones.
    assert (sample_course / "test-image.png").exists()
    assert (sample_course / "test-video.mp4").exists()
    ## Discovered via the markdown's own include=/output=/stout=/
    ## crash= attributes, not listed anywhere explicitly.
    assert (sample_course / "demo.out").exists()
    assert (sample_course / "repl_demo.stout").exists()
    assert (sample_course / "crash_demo.crash").exists()


def test_unchanged_rebuild_touches_nothing(sample_course):
    assert run_build(["full"]) == 0
    mtime_before = (sample_course / "markdown-features-1.full.html").stat().st_mtime

    assert run_build(["full"]) == 0

    mtime_after = (sample_course / "markdown-features-1.full.html").stat().st_mtime
    assert mtime_before == mtime_after


def test_editing_one_page_rebuilds_only_that_page(sample_course):
    assert run_build(["full"]) == 0
    other_mtime_before = (sample_course / "markdown-features-1.full.html").stat().st_mtime

    with open(sample_course / "markdown-features-2.md", "a") as fh:
        fh.write("\nan extra paragraph\n")
    assert run_build(["full"]) == 0

    other_mtime_after = (sample_course / "markdown-features-1.full.html").stat().st_mtime
    assert other_mtime_after == other_mtime_before


def test_single_target_file_selection(sample_course):
    """The `make introduction.tpp`-equivalent UX: naming a target file
    path directly, not a task/group name."""
    assert run_build(["question-groups-quiz.quiz.full.html"]) == 0

    assert (sample_course / "question-groups-quiz.quiz.full.html").exists()
    ## Nothing else got pulled in by naming just this one target.
    assert not (sample_course / "markdown-features-1.full.html").exists()


def test_clean_all_removes_every_targets_file(sample_course):
    """doit's own built-in "clean" subcommand only removes a task's
    targets if that task explicitly opts in via "clean": True -- every
    task-creator (core.py, python.py, and this fixture's own dodo.py)
    needs that key, or `tent-pole build clean --all` silently does
    nothing at all, the exact failure mode found live against the
    CSC1034 integration clone."""
    assert run_build(["full"]) == 0
    built = (
        "markdown-features-1.full.html", "markdown-features-2.full.html",
        "test-image.png", "test-video.mp4",
        "demo.out", "repl_demo.stout", "crash_demo.crash",
    )
    assert all((sample_course / name).exists() for name in built)

    ## doit's own Clean command has no explicit return, unlike Run --
    ## it comes back None, not 0. sys.exit(None) is still exit code 0
    ## for a real invocation, so this isn't a real-world problem, just
    ## not the same contract as run_build's other callers rely on.
    run_build(["clean", "-a"])

    assert not any((sample_course / name).exists() for name in built)
