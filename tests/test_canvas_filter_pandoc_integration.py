import shutil
import subprocess

import pytest

pandoc_missing = shutil.which("pandoc") is None


@pytest.mark.skipif(pandoc_missing, reason="pandoc not installed")
def test_pandoc_filter_end_to_end_highlights_python(tmp_path):
    """Real subprocess invocation -- pandoc actually loading and running
    this as a --filter, not just calling the Python functions directly.
    Relies on the venv's bin/ (with the canvas-filter console script)
    already being on PATH, as it is under `poetry run pytest`."""
    source = tmp_path / "doc.md"
    source.write_text("```python\ndef f(): pass\n```\n")

    result = subprocess.run(
        ["pandoc", str(source), "--filter=canvas-filter"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "<span" in result.stdout
    assert "def" in result.stdout
