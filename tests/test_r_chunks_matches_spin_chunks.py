"""r-chunks' split_chunks() is a deliberate R reimplementation of
spin_chunks.py's boundary rule, not shared code across the two
languages (r_support_design.md's implementation plan, step 7) -- this
is the fixture asserting the two actually agree, on real input."""

import pathlib
import shutil
import subprocess

import pytest

from tent_pole.spin_chunks import split_chunks

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


def r_chunk_names(path):
    result = subprocess.run(
        [RSCRIPT, str(SCRIPT), "--chunks", str(path)],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.splitlines()


def test_r_and_python_agree_on_demo_r():
    assert r_chunk_names(DEMO_R) == list(split_chunks(DEMO_R.read_text()))


def test_r_and_python_agree_on_edge_cases(tmp_path):
    """The same edge cases spin_chunks.py's own unit tests cover --
    prose before the first chunk, a chunk with no code, and trailing
    prose with nothing after it."""
    source = (
        "#' intro\n"
        "#+ a\n"
        "x <- 1\n"
        "#+ empty\n"
        "#+ b\n"
        "y <- 2\n"
        "#' closing remarks\n"
    )
    fixture = tmp_path / "fixture.R"
    fixture.write_text(source)

    assert r_chunk_names(fixture) == list(split_chunks(source))
