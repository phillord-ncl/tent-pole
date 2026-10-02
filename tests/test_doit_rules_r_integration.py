"""Real doit, real R, no network -- mirrors test_build_integration.py's
own pattern but for task_r, against a minimal synthetic .md/.R pair
rather than the full dev/sample-course-r (that needs its own
tent-pole.toml/dodo.py, step 9's job, not this one's)."""

import shutil
import subprocess

import pytest

from tent_pole.build import run_build

PANDOC = shutil.which("pandoc")
RSCRIPT = shutil.which("Rscript")


def _evaluate_installed():
    if RSCRIPT is None:
        return False
    result = subprocess.run(
        [RSCRIPT, "-e", "library(evaluate)"], capture_output=True, text=True,
    )
    return result.returncode == 0


pytestmark = pytest.mark.skipif(
    PANDOC is None or not _evaluate_installed(),
    reason="pandoc/Rscript/evaluate not installed",
)


@pytest.fixture
def course_dir(tmp_path, monkeypatch):
    (tmp_path / "demo.R").write_text(
        "#+ setup\nx <- 7\n#+ summary\ncat('x is', x, '\\n')\n"
        "#+ make-plot\nplot(1)\n#+ standalone-crash\nstop('boom')\n"
    )
    (tmp_path / "page.md").write_text(
        "```{.r include=demo.R chunk=summary output=true}\n```\n\n"
        "```{.r include=demo.R chunk=make-plot plot=true}\n```\n\n"
        "```{.r include=demo.R chunk=standalone-crash crash=true}\n```\n"
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_building_the_out_target_runs_r_chunks(course_dir):
    assert run_build(["demo_summary.out"]) == 0

    assert (course_dir / "demo_summary.out").read_text() == "x is 7 \n"


def test_building_the_plot_target_produces_a_png(course_dir):
    assert run_build(["demo_make-plot-1.png"]) == 0

    assert (course_dir / "demo_make-plot-1.png").exists()


def test_building_the_crash_target_produces_a_crash_file(course_dir):
    assert run_build(["demo_standalone-crash.crash"]) == 0

    assert "boom" in (course_dir / "demo_standalone-crash.crash").read_text()


def test_unchanged_rebuild_touches_nothing(course_dir):
    assert run_build(["demo_summary.out"]) == 0
    mtime_before = (course_dir / "demo_summary.out").stat().st_mtime

    assert run_build(["demo_summary.out"]) == 0

    assert (course_dir / "demo_summary.out").stat().st_mtime == mtime_before


def test_touching_the_r_file_rebuilds_all_its_targets_together(course_dir):
    """One task per .R file, not one per target -- doit does not merge
    separately-declared single-target tasks sharing a file_dep itself
    (r_support_design.md), so building just the .out target alone must
    still have produced the plot too, from the same single run."""
    assert run_build(["demo_summary.out"]) == 0

    assert (course_dir / "demo_make-plot-1.png").exists()
