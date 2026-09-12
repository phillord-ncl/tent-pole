import os
import pathlib
import shutil

import pytest

from tent_pole import include_deps_filter as deps_filter


def _resolve_pandoc():
    cabal_pandoc = os.path.expanduser("~/.cabal/bin/pandoc")
    if os.path.isfile(cabal_pandoc) and os.access(cabal_pandoc, os.X_OK):
        return cabal_pandoc
    return shutil.which("pandoc")


PANDOC = _resolve_pandoc()
pytestmark = pytest.mark.skipif(PANDOC is None, reason="pandoc not installed")

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "pandoc"


def test_code_with_include_and_output_produces_html_and_full_lines():
    html_line, full_line = deps_filter.generate(str(FIXTURES / "code-with-include.md"))

    assert html_line.startswith("code-with-include.html: ")
    assert "snippet.py" in html_line
    assert "snippet.py.tpf" in html_line
    assert "snippet.out" in html_line

    assert full_line.startswith("code-with-include.full.html: ")
    assert "snippet.py" in full_line
    assert "snippet.out" in full_line
    assert "snippet.py.tpf" not in full_line


def test_image_needs_tpf_for_html_and_raw_for_full():
    html_line, full_line = deps_filter.generate(str(FIXTURES / "image.md"))

    assert "diagram.png.tpf" in html_line
    assert "diagram.png" in full_line
    assert "diagram.png.tpf" not in full_line


def test_local_file_link_needs_tpf_for_html_and_raw_for_full():
    html_line, full_line = deps_filter.generate(str(FIXTURES / "local-file-link.md"))

    assert "handout.pdf.tpf" in html_line
    assert "handout.pdf" in full_line


def test_extensionless_link_is_not_a_dependency():
    html_line, full_line = deps_filter.generate(str(FIXTURES / "extensionless-link.md"))

    assert html_line == "extensionless-link.html: {}".format(
        str(FIXTURES / "extensionless-link.md")
    )
    assert full_line == "extensionless-link.full.html: {}".format(
        str(FIXTURES / "extensionless-link.md")
    )


def test_external_link_is_not_a_dependency():
    html_line, full_line = deps_filter.generate(str(FIXTURES / "external-link.md"))

    assert "example.com" not in html_line
    assert "example.com" not in full_line
