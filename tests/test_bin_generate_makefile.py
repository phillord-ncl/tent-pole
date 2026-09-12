import pathlib
import subprocess
import sys

SCRIPT = pathlib.Path(__file__).parent.parent / "tent_pole" / "bin" / "generate_makefile.py"


def run_generate_makefile(cwd):
    return subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=cwd, capture_output=True, text=True,
    )


def test_default_status_gets_out_target(tmp_path):
    (tmp_path / "demo.py").write_text("print('hi')\n")

    result = run_generate_makefile(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "demo.out: demo.py" in result.stdout
    assert "demo.out.tpf" in result.stdout
    assert "demo.py.tpf" in result.stdout


def test_status_crash_comment_gets_crash_target(tmp_path):
    (tmp_path / "crash_demo.py").write_text("## Status: Crash\nraise ValueError\n")

    result = run_generate_makefile(tmp_path)

    assert "crash_demo.crash: crash_demo.py" in result.stdout


def test_status_shell_comment_gets_stout_target(tmp_path):
    (tmp_path / "repl_demo.py").write_text("## Status: Shell\nx = 1\n")

    result = run_generate_makefile(tmp_path)

    assert "repl_demo.stout: repl_demo.py" in result.stdout


def test_test_prefixed_file_gets_test_out_target_not_out(tmp_path):
    """A test_*.py file gets .test_out regardless of any ## Status:
    comment -- checked before the comment-based branches, not after."""
    (tmp_path / "test_foo.py").write_text("def test_x(): assert True\n")

    result = run_generate_makefile(tmp_path)

    assert "test_foo.test_out: test_foo.py" in result.stdout
    assert "test_foo.out: test_foo.py" not in result.stdout
