import shutil

import pytest
import toml
from click.testing import CliRunner

from tent_pole import check


PANDOC = shutil.which("pandoc")
pandoc_required = pytest.mark.skipif(PANDOC is None, reason="pandoc not installed")


def write_module(tmp_path, name, identifier, items=None):
    directory = tmp_path / name
    directory.mkdir()
    module = {"identifier": identifier}
    if items is not None:
        module["items"] = items
    (directory / "tent-pole.toml").write_text(toml.dumps({"module": module}))
    return directory


def write_course(tmp_path, name, identifier):
    directory = tmp_path / name
    directory.mkdir()
    (directory / "tent-pole.toml").write_text(
        toml.dumps({"course": {"identifier": identifier}})
    )
    return directory


## name_collision

def test_name_collision_detects_shared_canvasname(tmp_path):
    wk1 = write_module(tmp_path, "wk1", "Week 1")
    wk2 = write_module(tmp_path, "wk2", "Week 2")
    (wk1 / "exercises.md").write_text("# Exercises\n")
    (wk2 / "exercises.md").write_text("# Exercises\n")

    findings = check.name_collision(str(tmp_path))

    assert len(findings) == 1
    assert "'exercises'" in findings[0]
    assert "wk1/exercises.md" in findings[0]
    assert "wk2/exercises.md" in findings[0]


def test_name_collision_ignores_course_directories(tmp_path):
    course = write_course(tmp_path, "lectures", "CSC1034")
    wk1 = write_module(tmp_path, "wk1", "Week 1")
    (course / "exercises.md").write_text("# Exercises\n")
    (wk1 / "exercises.md").write_text("# Exercises\n")

    assert check.name_collision(str(tmp_path)) == []


def test_name_collision_passes_for_distinct_names(tmp_path):
    wk1 = write_module(tmp_path, "wk1", "Week 1")
    wk2 = write_module(tmp_path, "wk2", "Week 2")
    (wk1 / "intro.md").write_text("# Intro\n")
    (wk2 / "setup.md").write_text("# Setup\n")

    assert check.name_collision(str(tmp_path)) == []


@pandoc_required
def test_name_collision_detects_shared_tpf_dependency(tmp_path):
    wk1 = write_module(tmp_path, "wk1", "Week 1")
    wk2 = write_module(tmp_path, "wk2", "Week 2")
    (wk1 / "intro.md").write_text("[Handout](handout.pdf)\n")
    (wk2 / "setup.md").write_text("[Handout](handout.pdf)\n")

    findings = check.name_collision(str(tmp_path))

    file_findings = [f for f in findings if f.startswith("file ")]
    assert len(file_findings) == 1
    assert "handout.pdf" in file_findings[0]


## stamp_collision

def test_stamp_collision_detects_shared_page_url(tmp_path):
    wk1 = tmp_path / "wk1"
    wk2 = tmp_path / "wk2"
    wk1.mkdir()
    wk2.mkdir()
    (wk1 / "exercises.tpp").write_text(toml.dumps({"url": "exercises", "page_id": 1}))
    (wk2 / "exercises.tpp").write_text(toml.dumps({"url": "exercises", "page_id": 1}))

    findings = check.stamp_collision(str(tmp_path))

    assert len(findings) == 1
    assert "exercises" in findings[0]
    assert "wk1/exercises.tpp" in findings[0]
    assert "wk2/exercises.tpp" in findings[0]


def test_stamp_collision_ignores_distinct_pages(tmp_path):
    wk1 = tmp_path / "wk1"
    wk2 = tmp_path / "wk2"
    wk1.mkdir()
    wk2.mkdir()
    (wk1 / "intro.tpp").write_text(toml.dumps({"url": "intro", "page_id": 1}))
    (wk2 / "setup.tpp").write_text(toml.dumps({"url": "setup", "page_id": 2}))

    assert check.stamp_collision(str(tmp_path)) == []


def test_stamp_collision_detects_shared_file_identity(tmp_path):
    wk1 = tmp_path / "wk1"
    wk2 = tmp_path / "wk2"
    wk1.mkdir()
    wk2.mkdir()
    (wk1 / "handout.pdf.tpf").write_text(toml.dumps({"filename": "handout.pdf", "id": 99}))
    (wk2 / "handout.pdf.tpf").write_text(toml.dumps({"filename": "handout.pdf", "id": 99}))

    findings = check.stamp_collision(str(tmp_path))

    assert len(findings) == 1
    assert "handout.pdf" in findings[0]


## unreferenced

def test_unreferenced_flags_page_missing_from_items(tmp_path):
    wk1 = write_module(tmp_path, "wk1", "Week 1", items=[{"id": "intro"}])
    (wk1 / "intro.md").write_text("# Intro\n")
    (wk1 / "orphan.md").write_text("# Orphan\n")

    findings = check.unreferenced(str(tmp_path))

    assert len(findings) == 1
    assert "orphan.md" in findings[0]


def test_unreferenced_passes_when_all_listed(tmp_path):
    wk1 = write_module(tmp_path, "wk1", "Week 1", items=[{"id": "intro"}])
    (wk1 / "intro.md").write_text("# Intro\n")

    assert check.unreferenced(str(tmp_path)) == []


def test_unreferenced_matches_underscored_id_to_hyphenated_name(tmp_path):
    """module.py's own resolution runs an item's id through
    canvasname_from_path too -- an id is a raw filename stem (often
    underscored), not already a canvasname, so this must not
    false-positive just because the id and the page name are spelled
    differently."""
    wk1 = write_module(
        tmp_path, "wk1", "Week 1", items=[{"id": "starting_python"}]
    )
    (wk1 / "starting_python.md").write_text("# Starting Python\n")

    assert check.unreferenced(str(tmp_path)) == []


def test_unreferenced_ignores_course_directories(tmp_path):
    course = write_course(tmp_path, "lectures", "CSC1034")
    (course / "slides.md").write_text("# Slides\n")

    assert check.unreferenced(str(tmp_path)) == []


## CLI

def test_check_cli_reports_without_failing(tmp_path, monkeypatch):
    wk1 = write_module(tmp_path, "wk1", "Week 1", items=[{"id": "intro"}])
    (wk1 / "intro.md").write_text("# Intro\n")
    (wk1 / "orphan.md").write_text("# Orphan\n")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(check.check, ["unreferenced"])

    assert result.exit_code == 0, result.output
    assert "orphan.md" in result.output


def test_check_cli_strict_fails_on_findings(tmp_path, monkeypatch):
    wk1 = write_module(tmp_path, "wk1", "Week 1", items=[{"id": "intro"}])
    (wk1 / "intro.md").write_text("# Intro\n")
    (wk1 / "orphan.md").write_text("# Orphan\n")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(check.check, ["--strict", "unreferenced"])

    assert result.exit_code != 0


def test_check_cli_ok_when_clean(tmp_path, monkeypatch):
    wk1 = write_module(tmp_path, "wk1", "Week 1", items=[{"id": "intro"}])
    (wk1 / "intro.md").write_text("# Intro\n")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(check.check, ["unreferenced"])

    assert result.exit_code == 0
    assert "OK" in result.output


def test_check_cli_requires_at_least_one_linter(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(check.check, [])
    assert result.exit_code != 0


def test_check_cli_rejects_unknown_linter(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(check.check, ["not-a-real-linter"])
    assert result.exit_code != 0


def test_check_cli_runs_multiple_linters(tmp_path, monkeypatch):
    wk1 = write_module(tmp_path, "wk1", "Week 1", items=[{"id": "intro"}])
    wk2 = write_module(tmp_path, "wk2", "Week 2")
    (wk1 / "intro.md").write_text("# Intro\n")
    (wk1 / "exercises.md").write_text("# Exercises\n")
    (wk2 / "exercises.md").write_text("# Exercises\n")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(check.check, ["name-collision", "unreferenced"])

    assert result.exit_code == 0, result.output
    assert "[name-collision]" in result.output
    assert "[unreferenced]" in result.output


def test_check_cli_all_alias_runs_every_linter(tmp_path, monkeypatch):
    wk1 = write_module(tmp_path, "wk1", "Week 1", items=[{"id": "intro"}])
    wk2 = write_module(tmp_path, "wk2", "Week 2")
    (wk1 / "intro.md").write_text("# Intro\n")
    (wk1 / "orphan.md").write_text("# Orphan\n")
    (wk1 / "exercises.md").write_text("# Exercises\n")
    (wk2 / "exercises.md").write_text("# Exercises\n")
    (wk1 / "exercises.tpp").write_text(toml.dumps({"url": "exercises"}))
    (wk2 / "exercises.tpp").write_text(toml.dumps({"url": "exercises"}))
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(check.check, ["all"])

    assert result.exit_code == 0, result.output
    assert "[name-collision]" in result.output
    assert "[stamp-collision]" in result.output
    assert "[unreferenced]" in result.output


def test_check_cli_build_alias_runs_only_name_collision(tmp_path, monkeypatch):
    wk1 = write_module(tmp_path, "wk1", "Week 1")
    wk2 = write_module(tmp_path, "wk2", "Week 2")
    (wk1 / "exercises.md").write_text("# Exercises\n")
    (wk2 / "exercises.md").write_text("# Exercises\n")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(check.check, ["build"])

    assert result.exit_code == 0, result.output
    assert "[name-collision]" in result.output
    assert "[stamp-collision]" not in result.output
    assert "[unreferenced]" not in result.output
