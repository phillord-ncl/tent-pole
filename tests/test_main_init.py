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


def test_init_writes_toml_and_hello(tmp_path, monkeypatch):
    """No Makefile: `tent-pole build` needs no local build file at all
    to work in a fresh project -- its built-in doit rules cover a
    plain markdown-pages course by default, so there's nothing for
    init to scaffold there any more (see doit_rules/__init__.py)."""
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["init"])

    assert result.exit_code == 0, result.output
    assert not (tmp_path / "Makefile").exists()
    assert (tmp_path / "hello.md").read_text() == "# Hello\n"
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
    assert (tmp_path / "tent-pole.toml").exists()
    assert (tmp_path / "hello.md").exists()
