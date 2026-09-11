import datetime
import os
import pathlib
import re
import shutil
import subprocess

import pytest

from tent_pole import canvas_filter

TENT_POLE_MARKER_PATTERN = re.compile(
    r'<span style="display:none" data-tent-pole="managed" data-compiled-at="[^"]*"></span>\n?'
)


def strip_tent_pole_marker(html):
    return TENT_POLE_MARKER_PATTERN.sub("", html)


def _resolve_pandoc():
    """Prefer a cabal-installed pandoc (~/.cabal/bin/pandoc) over
    whatever the system package manager happens to have on PATH -- the
    whole point of installing it via cabal is to pin an exact version
    rather than track distro drift, so tests should honour that choice
    when it's present rather than silently falling back to an older
    system pandoc."""
    cabal_pandoc = os.path.expanduser("~/.cabal/bin/pandoc")
    if os.path.isfile(cabal_pandoc) and os.access(cabal_pandoc, os.X_OK):
        return cabal_pandoc
    return shutil.which("pandoc")


PANDOC = _resolve_pandoc()
pandoc_missing = PANDOC is None
pytestmark = pytest.mark.skipif(pandoc_missing, reason="pandoc not installed")

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "pandoc"


def run_pandoc_filter(fixture_name):
    """Real subprocess invocation -- pandoc actually loading and running
    this as a --filter, not just calling the Python functions directly.
    Relies on the venv's bin/ (with the canvas-filter console script)
    already being on PATH, as it is under `poetry run pytest`. Fixtures
    live in tests/fixtures/pandoc/ and are run in place (read-only --
    canvas-filter never writes into the document/.tpf files it reads)."""
    result = subprocess.run(
        [PANDOC, fixture_name, "--filter=canvas-filter"],
        cwd=FIXTURES,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_python_code_is_highlighted():
    html = run_pandoc_filter("python-code.md")
    assert "<span" in html
    assert "def" in html


def test_unknown_language_falls_back_to_plain():
    html = run_pandoc_filter("unknown-language-code.md")
    assert "some plain content here" in html
    ## "no highlighting spans wrapping the content" -- not "no spans at
    ## all in the document": every document now carries the tent-pole
    ## marker span (added by add_tent_pole_marker), which is unrelated.
    content_only = strip_tent_pole_marker(html)
    assert "<span" not in content_only.replace("<span></span>", "")


def test_plain_code_block_unchanged():
    html = run_pandoc_filter("plain-code.md")
    assert "<pre><code>no language at all" in html


def test_code_with_include_and_output_attributes():
    """Confirms pandoc's own attribute syntax ({.python include=...
    output=true}) actually parses into what code_filter expects --
    the unit tests in test_canvas_filter.py construct panflute elements
    directly and never exercise pandoc's real markdown parsing for this."""
    html = run_pandoc_filter("code-with-include.md")
    assert "<span" in html  # the included snippet.py, highlighted
    assert "Take from: snippet.py" in html
    assert "../files/55/download" in html  # from snippet.py.tpf's id
    assert "Outputs:" in html
    assert "hi" in html  # from snippet.out


def test_external_link_untouched():
    html = run_pandoc_filter("external-link.md")
    assert 'href="https://example.com/foo"' in html


def test_extensionless_local_link_untouched():
    html = run_pandoc_filter("extensionless-link.md")
    assert 'href="some-page"' in html


def test_local_file_link_rewritten_via_tpf():
    html = run_pandoc_filter("local-file-link.md")
    assert 'href="../files/99/download"' in html


def test_mp4_link_becomes_video_iframe():
    html = run_pandoc_filter("mp4-link.md")
    assert "m123" in html
    assert "media_objects_iframe" in html


def test_image_becomes_canvas_preview_url():
    html = run_pandoc_filter("image.md")
    assert "courses/16807/files/7/preview" in html
    ## Regression: elem.title (only the optional quoted title after the
    ## url) used to be used for alt text, silently producing alt="" for
    ## the plain ![alt](url) form this fixture uses.
    assert 'alt="My Diagram"' in html


def test_image_with_explicit_alt_attribute():
    html = run_pandoc_filter("image-explicit-alt.md")
    assert "courses/16807/files/7/preview" in html
    assert 'alt="An explicit alt text"' in html
    ## The whole point of the ![](url){alt="..."} form: empty bracket
    ## content means pandoc never promotes this into a Figure, so no
    ## unwanted visible <figcaption> appears.
    assert "<figcaption" not in html


def test_output_carries_tent_pole_marker_with_extractable_timestamp():
    html = run_pandoc_filter("plain-code.md")
    compiled_at = canvas_filter.extract_compiled_at(html)

    assert compiled_at is not None
    ## Round-trips through datetime.fromisoformat without raising
    datetime.datetime.fromisoformat(compiled_at)
