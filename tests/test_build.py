"""Offline tests for tent_pole.build's bare-stem target resolution --
letting `tent-pole build programming` mean `tent-pole build
programming.tpp` without the caller needing to already know tent-pole's
internal stamp-file naming convention. The referenced-script cases need
real pandoc, like include_deps_filter's own pandoc-integration tests."""

import shutil

import pytest

from tent_pole.build import _resolve_bare_name, _resolve_argv

PANDOC = shutil.which("pandoc")


@pytest.fixture
def course_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_md_stem_resolves_to_tpp(course_dir):
    (course_dir / "programming.md").write_text("hello\n")
    assert _resolve_bare_name("programming") == "programming.tpp"


def test_quiz_md_stem_resolves_to_tpq(course_dir):
    (course_dir / "quiz1.quiz.md").write_text("hello\n")
    assert _resolve_bare_name("quiz1") == "quiz1.tpq"


def test_quiz_md_checked_before_plain_md(course_dir):
    """A quiz's own stem never collides with plain .md handling since
    *.quiz.md is also *.md -- but the quiz check runs first regardless."""
    (course_dir / "quiz1.quiz.md").write_text("hello\n")
    (course_dir / "quiz1.md").write_text("hello\n")
    assert _resolve_bare_name("quiz1") == "quiz1.tpq"


def test_plain_script_stem_resolves_to_out(course_dir):
    (course_dir / "hello_world.py").write_text("print('hi')\n")
    assert _resolve_bare_name("hello_world") == "hello_world.out"


def test_crash_marked_script_stem_resolves_to_crash(course_dir):
    (course_dir / "broken.py").write_text("## Status: Crash\nraise SystemExit(1)\n")
    assert _resolve_bare_name("broken") == "broken.crash"


def test_shell_marked_script_stem_resolves_to_stout(course_dir):
    (course_dir / "repl.py").write_text("## Status: Shell\nx = 1\n")
    assert _resolve_bare_name("repl") == "repl.stout"


def test_test_prefixed_script_stem_resolves_to_test_out(course_dir):
    (course_dir / "test_stats.py").write_text("def test_x(): assert True\n")
    assert _resolve_bare_name("test_stats") == "test_stats.test_out"


def test_plain_asset_resolves_to_tpf(course_dir):
    (course_dir / "diagram.png").write_bytes(b"\x89PNG")
    assert _resolve_bare_name("diagram.png") == "diagram.png.tpf"


def test_unknown_name_passed_through_unchanged(course_dir):
    assert _resolve_bare_name("pages") == "pages"


def test_already_qualified_name_never_reinterpreted_as_an_asset(course_dir):
    """The real bug this guards against: if "foo.tpp" already exists
    on disk (already pushed once), it must not be treated as a raw
    asset needing its own "foo.tpp.tpf" push."""
    (course_dir / "foo.tpp").write_text("")
    assert _resolve_bare_name("foo.tpp") == "foo.tpp"


def test_resolve_argv_leaves_flags_and_subtask_names_alone(course_dir):
    (course_dir / "programming.md").write_text("hello\n")
    argv = ["-n", "4", "programming", "pages:foo.tpp", "var=1"]
    assert _resolve_argv(argv) == ["-n", "4", "programming.tpp", "pages:foo.tpp", "var=1"]


@pytest.mark.skipif(PANDOC is None, reason="pandoc not installed")
def test_referenced_script_in_a_different_directory_resolves_by_basename(tmp_path, monkeypatch):
    """The real case this exists for: hello_world.py lives in ../python/
    relative to the page that include=s it -- a sibling of the page's
    own directory, not inside it -- and a bare "hello_world" must still
    resolve correctly."""
    (tmp_path / "python").mkdir()
    (tmp_path / "python" / "hello_world.py").write_text("print('hi')\n")
    wk1 = tmp_path / "wk1"
    wk1.mkdir()
    (wk1 / "page.md").write_text("```{.python include=../python/hello_world.py}\n```\n")
    monkeypatch.chdir(wk1)

    assert _resolve_bare_name("hello_world") == "../python/hello_world.out"


@pytest.mark.skipif(PANDOC is None, reason="pandoc not installed")
def test_referenced_crash_script_in_a_different_directory_resolves_to_crash(tmp_path, monkeypatch):
    (tmp_path / "python").mkdir()
    (tmp_path / "python" / "broken.py").write_text("## Status: Crash\nraise SystemExit(1)\n")
    wk1 = tmp_path / "wk1"
    wk1.mkdir()
    (wk1 / "page.md").write_text("```{.python include=../python/broken.py}\n```\n")
    monkeypatch.chdir(wk1)

    assert _resolve_bare_name("broken") == "../python/broken.crash"
