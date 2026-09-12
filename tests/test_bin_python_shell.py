import pathlib
import subprocess
import sys

SCRIPT = pathlib.Path(__file__).parent.parent / "tent_pole" / "bin" / "python-shell"


def run_shell(source):
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=source, capture_output=True, text=True,
    )


def test_echoes_source_with_prompts():
    result = run_shell("x = 1\n")
    assert result.returncode == 0
    assert ">>> x = 1" in result.stdout


def test_traceback_from_a_raising_line_lands_in_the_transcript():
    """The whole reason this script exists: capture a snippet's real
    interactive-shell output, including a crash, so it can be
    redirected straight into a .stout file. Shell.write() used to be
    missing `self`, so the traceback text landed in the wrong
    parameter and a stray repr of the console object got printed
    instead -- and on a host whose sys.excepthook is customised (e.g.
    Ubuntu's apport), the traceback bypasses write() entirely and goes
    to stderr instead of the redirected transcript."""
    result = run_shell('raise ValueError("boom")\n')
    assert result.returncode == 0
    assert "ValueError: boom" in result.stdout
    assert "Shell object at" not in result.stdout
    assert result.stderr == ""
