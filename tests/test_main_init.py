import os
import subprocess

import pytest
from click.testing import CliRunner

from tent_pole.main import main


@pytest.fixture(autouse=True)
def no_ambient_git_dir(monkeypatch):
    """git honours GIT_DIR/GIT_WORK_TREE from the environment over cwd --
    set by git itself when running these tests from a commit hook, which
    would otherwise point every `git init`/`git rev-parse` below at the
    real repo instead of tmp_path."""
    monkeypatch.delenv("GIT_DIR", raising=False)
    monkeypatch.delenv("GIT_WORK_TREE", raising=False)


def test_init_writes_makefile_toml_and_hello(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["init"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "Makefile").exists()
    assert (tmp_path / "hello.md").read_text() == "# Hello\n"
    assert "TENT_POLE ?= tent-pole\n" in (tmp_path / "Makefile").read_text()
    assert (tmp_path / ".git").exists()

    toml = (tmp_path / "tent-pole.toml").read_text()
    assert 'id = "COURSE_NAME"' in toml
    assert 'identifier = "Hello World Module"' in toml
    assert '{id="hello"}' in toml


def test_init_never_overwrites_an_existing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "hello.md").write_text("# Keep me\n")

    result = CliRunner().invoke(main, ["init"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "hello.md").read_text() == "# Keep me\n"
    assert "already exists" in result.output


def test_init_skips_git_init_inside_existing_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    before = (tmp_path / ".git").stat().st_mtime

    result = CliRunner().invoke(main, ["init"])

    assert result.exit_code == 0, result.output
    assert "Already inside a git repository" in result.output
    assert (tmp_path / ".git").stat().st_mtime == before


def test_init_no_git_flag_skips_git_init(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["init", "--no-git"])

    assert result.exit_code == 0, result.output
    assert not (tmp_path / ".git").exists()
    assert (tmp_path / "Makefile").exists()
    assert (tmp_path / "tent-pole.toml").exists()
    assert (tmp_path / "hello.md").exists()


def test_init_tent_pole_dev_writes_one_script_dev_mk_and_symlinks(tmp_path, monkeypatch):
    """--tent-pole-dev must work for a project living anywhere, not just
    below the tent-pole checkout -- unlike a bare `poetry run tent-pole`
    embedded in the Makefile, which only resolves pyproject.toml when
    invoked from inside/below the checkout. The base Makefile stays
    exactly as the non-dev case, plus one -include line: dev-scripts/
    dev.mk overrides TENT_POLE/CANVAS_FILTER/CODE_INCLUDE_FILTER/
    INCLUDE_DEPS_FILTER, all pointing at dev-scripts/tent-pole-dev.sh
    -- directly for TENT_POLE (a command prefix, so it can carry the
    tool name as a trailing word), and via a symlink per filter, since
    pandoc's --filter=X execs X directly with no room for an argument.
    tent-pole-dev.sh picks the tool up from $1 when invoked under its
    own name, or from its own invoked name otherwise."""
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["init", "--tent-pole-dev", "--no-git"])

    assert result.exit_code == 0, result.output
    makefile = (tmp_path / "Makefile").read_text()
    assert makefile.startswith("-include dev-scripts/dev.mk\n\n")
    assert "TENT_POLE ?=" in makefile.splitlines()[2]

    dev_mk = (tmp_path / "dev-scripts" / "dev.mk").read_text()
    assert "TENT_POLE ?= dev-scripts/tent-pole-dev.sh tent-pole\n" in dev_mk
    assert "CANVAS_FILTER ?= dev-scripts/canvas-filter.sh\n" in dev_mk
    assert "CODE_INCLUDE_FILTER ?= dev-scripts/code-include-filter.sh\n" in dev_mk
    assert "INCLUDE_DEPS_FILTER ?= dev-scripts/include-deps-filter.sh\n" in dev_mk

    impl = tmp_path / "dev-scripts" / "tent-pole-dev.sh"
    assert impl.exists()
    assert not impl.is_symlink()
    assert os.access(impl, os.X_OK)
    content = impl.read_text()
    assert "poetry run" in content
    assert 'if [ "$NAME" = "tent-pole-dev" ]; then' in content
    ## The checkout path is baked in absolute, so the wrapper works
    ## regardless of where it's later invoked from.
    cd_line = next(line for line in content.splitlines() if line.startswith("cd "))
    assert os.path.isabs(cd_line.split()[1])

    for name in ["canvas-filter.sh", "code-include-filter.sh", "include-deps-filter.sh"]:
        symlink = tmp_path / "dev-scripts" / name
        assert symlink.is_symlink()
        assert os.readlink(symlink) == "tent-pole-dev.sh"
        assert os.access(symlink, os.X_OK)


def test_init_tent_pole_dev_errors_without_a_poetry_checkout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    no_checkout = tmp_path / "not-a-checkout"
    no_checkout.mkdir()
    monkeypatch.setattr("tent_pole.main.__checkout_root", lambda: str(no_checkout))

    result = CliRunner().invoke(main, ["init", "--tent-pole-dev", "--no-git"])

    assert result.exit_code != 0
    assert "pyproject.toml" in result.output
    assert not (tmp_path / "Makefile").exists()
