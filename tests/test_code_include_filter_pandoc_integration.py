import os
import pathlib
import shutil
import subprocess

import pytest


def _resolve_pandoc():
    """Prefer a cabal-installed pandoc (~/.cabal/bin/pandoc) over
    whatever the system package manager happens to have on PATH -- see
    test_canvas_filter_pandoc_integration.py's identical helper for the
    reasoning."""
    cabal_pandoc = os.path.expanduser("~/.cabal/bin/pandoc")
    if os.path.isfile(cabal_pandoc) and os.access(cabal_pandoc, os.X_OK):
        return cabal_pandoc
    return shutil.which("pandoc")


PANDOC = _resolve_pandoc()
pandoc_missing = PANDOC is None
pytestmark = pytest.mark.skipif(pandoc_missing, reason="pandoc not installed")

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "pandoc"


def run_pandoc_filter(fixture_name):
    """Real subprocess invocation, same rationale as
    test_canvas_filter_pandoc_integration.py's run_pandoc_filter --
    confirms pandoc's own attribute-syntax parsing feeds code_filter
    what it expects, not just that the Python function works in
    isolation."""
    result = subprocess.run(
        [PANDOC, fixture_name, "--filter=code-include-filter"],
        cwd=FIXTURES,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_include_produces_highlighted_codeblock_via_pandocs_own_writer():
    html = run_pandoc_filter("code-include-filter.md")
    ## pandoc's own Skylighting highlighting (not Pygments) -- the
    ## whole point of staying a CodeBlock instead of a RawBlock.
    assert "sourceCode python" in html
    assert "print" in html
    assert "hi" in html  # from snippet.out via output=true
    assert "Outputs:" in html


def test_plain_code_block_without_include_unchanged():
    html = run_pandoc_filter("plain-code.md")
    assert "no language at all" in html


def test_pdf_output_actually_contains_the_included_code(tmp_path):
    """The concrete reason this filter exists rather than reusing
    canvas-filter: canvas-filter's RawBlock('html', ...) is dropped
    entirely by a non-HTML writer, so its highlighted code silently
    vanishes from a PDF. Confirms that doesn't happen here by rendering
    all the way to PDF and checking the text layer."""
    pdf_engine = shutil.which("pdflatex") or shutil.which("xelatex") or shutil.which("tectonic")
    if pdf_engine is None:
        pytest.skip("no PDF engine (pdflatex/xelatex/tectonic) installed")

    out_pdf = tmp_path / "out.pdf"
    result = subprocess.run(
        [PANDOC, "code-include-filter.md", "--filter=code-include-filter",
         "-s", "-o", str(out_pdf)],
        cwd=FIXTURES,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert out_pdf.exists()

    pdftotext = shutil.which("pdftotext")
    if pdftotext is None:
        pytest.skip("pdftotext not installed to verify PDF text content")
    text = subprocess.run(
        [pdftotext, str(out_pdf), "-"], capture_output=True, text=True
    ).stdout
    assert "print" in text
