"""Integration tests for tent_pole/bin/r-chunks -- real R, real
evaluate(), no network. Skipped if either is missing (see
r_support_design.md's "Empirical findings": installed from CRAN into
a scratch library during design, same as the pandoc/ffmpeg skip used
elsewhere)."""

import pathlib
import shutil
import subprocess

import pytest

RSCRIPT = shutil.which("Rscript")


def _evaluate_installed():
    if RSCRIPT is None:
        return False
    result = subprocess.run(
        [RSCRIPT, "-e", "library(evaluate)"], capture_output=True, text=True,
    )
    return result.returncode == 0


pytestmark = pytest.mark.skipif(
    not _evaluate_installed(), reason="Rscript/evaluate not installed"
)

SCRIPT = pathlib.Path(__file__).parent.parent / "tent_pole" / "bin" / "r-chunks"
DEMO_R = pathlib.Path(__file__).parent.parent / "dev" / "sample-course-r" / "demo.R"


def run_r_chunks(*args):
    return subprocess.run(
        [RSCRIPT, str(SCRIPT), *args], capture_output=True, text=True,
    )


@pytest.fixture
def course_dir(tmp_path):
    shutil.copy(DEMO_R, tmp_path / "demo.R")
    return tmp_path


def test_chunks_flag_lists_chunk_names_in_order(course_dir):
    result = run_r_chunks("--chunks", str(course_dir / "demo.R"))

    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        "setup", "summary-stats", "make-plot", "distribution-plot",
        "standalone-crash",
    ]


def test_run_writes_output_for_a_printing_chunk(course_dir):
    result = run_r_chunks(str(course_dir / "demo.R"))

    assert result.returncode == 0
    assert (course_dir / "demo_summary-stats.out").read_text() == (
        "Mean: 18 \nSD: 13.49 \n"
    )


def test_run_writes_a_transcript_with_prompts(course_dir):
    run_r_chunks(str(course_dir / "demo.R"))

    stout = (course_dir / "demo_summary-stats.stout").read_text()
    assert '> cat("Mean:", mean(data), "\\n")' in stout
    assert "Mean: 18" in stout


def test_run_writes_an_empty_out_for_a_chunk_with_no_text_output(course_dir):
    """Writes unconditionally for every chunk, per the design plan --
    setup only assigns a variable, but still gets a (empty) .out."""
    run_r_chunks(str(course_dir / "demo.R"))

    assert (course_dir / "demo_setup.out").read_text() == ""


def test_run_writes_one_png_per_plot(course_dir):
    run_r_chunks(str(course_dir / "demo.R"))

    assert (course_dir / "demo_make-plot-1.png").exists()
    assert (course_dir / "demo_distribution-plot-1.png").exists()


def test_run_writes_a_crash_file_for_the_erroring_chunk(course_dir):
    run_r_chunks(str(course_dir / "demo.R"))

    crash = (course_dir / "demo_standalone-crash.crash").read_text()
    assert "non-numeric argument to binary operator" in crash


def test_nothing_after_a_crash_is_written(tmp_path):
    """The constraint r_support_design.md documents: a crash= chunk
    must be the last one anything else depends on, because nothing
    after it actually runs."""
    source = tmp_path / "ordering.R"
    source.write_text("#+ a\n1 + 1\n#+ b\nstop('boom')\n#+ c\ncat('after')\n")

    result = run_r_chunks(str(source))

    assert result.returncode == 0
    assert (tmp_path / "ordering_a.out").exists()
    assert (tmp_path / "ordering_b.crash").exists()
    assert not (tmp_path / "ordering_c.out").exists()
