import os

import toml
from click.testing import CliRunner

from tent_pole import config


def write_toml(path, data):
    with open(path, "w") as fh:
        toml.dump(data, fh)
    return str(path)


def test_get_maybe_returns_value_for_present_key():
    assert config.get_maybe({"a": {"b": 1}}, "a/b") == 1


def test_get_maybe_returns_none_for_missing_key():
    assert config.get_maybe({"a": {"b": 1}}, "a/c") is None


def test_fetch_config_later_file_wins_on_conflict(tmp_path):
    first = write_toml(tmp_path / "first.toml", {"course": {"id": "111"}})
    second = write_toml(tmp_path / "second.toml", {"course": {"id": "222"}})

    merged = config.fetch_config([first, second])

    assert merged["course"]["id"] == "222"


def test_fetch_config_deep_merges_distinct_keys(tmp_path):
    first = write_toml(tmp_path / "first.toml", {"general": {"api_key": "k"}})
    second = write_toml(tmp_path / "second.toml", {"course": {"id": "111"}})

    merged = config.fetch_config([first, second])

    assert merged["general"]["api_key"] == "k"
    assert merged["course"]["id"] == "111"


def test_fetch_config_skips_missing_files(tmp_path):
    present = write_toml(tmp_path / "present.toml", {"course": {"id": "111"}})
    missing = str(tmp_path / "does-not-exist.toml")

    merged = config.fetch_config([missing, present])

    assert merged["course"]["id"] == "111"


def test_fetch_config_returns_empty_dict_if_no_files_exist(tmp_path):
    """Regression test: fetch_config used to raise TypeError when every
    candidate file was missing (functools.reduce over an empty sequence
    with no initial value). Fixed by passing {} as the initial value --
    now it correctly returns an empty config instead of crashing."""
    missing = str(tmp_path / "does-not-exist.toml")

    assert config.fetch_config([missing]) == {}


def test_ancestor_config_paths_stops_at_git_boundary(tmp_path):
    root = tmp_path / "course-repo"
    deep = root / "a" / "b" / "c"
    deep.mkdir(parents=True)
    (root / ".git").mkdir()

    paths = config.ancestor_config_paths(str(deep))
    dirs = [os.path.dirname(p) for p in paths]

    assert all(p.endswith("tent-pole.toml") for p in paths)
    assert dirs[0] == str(root)  # repo root first, not the filesystem root
    assert dirs[-1] == str(deep)  # most specific (start_dir) last
    # an unbroken parent-to-child chain, each dir the direct parent of the next
    for parent, child in zip(dirs, dirs[1:]):
        assert os.path.dirname(child) == parent
    assert len(dirs) == len(set(dirs))  # no duplicates


def test_ancestor_config_paths_git_as_file_also_counts_as_boundary(tmp_path):
    """A worktree's .git is a file (pointing at the shared repo), not a
    directory -- must work as a boundary just as well as a real .git/."""
    root = tmp_path / "course-repo-worktree"
    deep = root / "a"
    deep.mkdir(parents=True)
    (root / ".git").write_text("gitdir: /somewhere/else\n")

    paths = config.ancestor_config_paths(str(deep))
    dirs = [os.path.dirname(p) for p in paths]

    assert dirs[0] == str(root)


def test_ancestor_config_paths_never_crawls_to_filesystem_root_without_a_git_boundary(tmp_path):
    """The actual risk being guarded against: no .git anywhere above
    start_dir must mean no cascade at all, not a fall-through crawl all
    the way up to / (which could pick up an unrelated tent-pole.toml)."""
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)

    paths = config.ancestor_config_paths(str(deep))

    assert paths == [os.path.join(str(deep), "tent-pole.toml")]


def test_cascade_lets_a_repo_root_config_apply_to_a_subdirectory(tmp_path):
    """The actual motivating case: a course-id set once at a course repo's
    root should apply to every subproject directory beneath it, without
    repeating it in each one."""
    root = tmp_path / "course-repo"
    sub = root / "project-1"
    sub.mkdir(parents=True)
    (root / ".git").mkdir()
    write_toml(root / "tent-pole.toml", {"course": {"id": "12345"}})

    merged = config.fetch_config(config.ancestor_config_paths(str(sub)))

    assert merged["course"]["id"] == "12345"


def test_subdirectory_config_overrides_repo_root_on_conflict(tmp_path):
    root = tmp_path / "course-repo"
    sub = root / "project-1"
    sub.mkdir(parents=True)
    (root / ".git").mkdir()
    write_toml(root / "tent-pole.toml", {"course": {"id": "12345"}})
    write_toml(sub / "tent-pole.toml", {"course": {"id": "OVERRIDE"}})

    merged = config.fetch_config(config.ancestor_config_paths(str(sub)))

    assert merged["course"]["id"] == "OVERRIDE"


def test_cascade_lets_a_repo_root_beta_flag_apply_to_a_subdirectory(tmp_path):
    """The motivating case for the config-file beta opt-in: a course
    repo can set `beta = true` once at its root and have it apply
    everywhere beneath it, the same way course/id already does."""
    root = tmp_path / "course-repo"
    sub = root / "project-1"
    sub.mkdir(parents=True)
    (root / ".git").mkdir()
    write_toml(root / "tent-pole.toml", {"beta": True})

    merged = config.fetch_config(config.ancestor_config_paths(str(sub)))

    assert merged["beta"] is True


def test_cascade_ignores_config_above_the_repo_boundary(tmp_path):
    """A tent-pole.toml sitting outside the repo (above the .git
    boundary) must never apply -- this is the whole point of the fix."""
    root = tmp_path / "course-repo"
    sub = root / "project-1"
    sub.mkdir(parents=True)
    (root / ".git").mkdir()
    write_toml(tmp_path / "tent-pole.toml", {"course": {"id": "UNRELATED"}})

    merged = config.fetch_config(config.ancestor_config_paths(str(sub)))

    assert merged == {}


def test_config_api_url_falls_back_to_default(monkeypatch):
    monkeypatch.setattr(config, "CONFIG", {})
    assert config.config_api_url() == config.DEFAULT_API_URL


def test_config_api_url_uses_configured_value(monkeypatch):
    monkeypatch.setattr(
        config, "CONFIG", {"general": {"api_url": "https://ncl.beta.instructure.com"}}
    )
    assert config.config_api_url() == "https://ncl.beta.instructure.com"


## TENT_POLE_USE_TEST_CONFIG: opt-in only -- unset (the default in every
## test above and in ordinary use) must never let a leftover [dev] test_*
## value leak into [general]/[course] resolution.

def test_use_test_config_false_by_default(monkeypatch):
    monkeypatch.delenv("TENT_POLE_USE_TEST_CONFIG", raising=False)
    assert config.use_test_config() is False


def test_use_test_config_true_when_env_var_set(monkeypatch):
    monkeypatch.setenv("TENT_POLE_USE_TEST_CONFIG", "1")
    assert config.use_test_config() is True


def test_use_test_config_true_when_beta_set_in_config(monkeypatch):
    """The config-file route: a repo whose tent-pole.toml says
    `beta = true` targets beta from any invocation, not just ones that
    went through a Makefile setting the env var -- this is what a
    direct `tent-pole ...` call from the command line, or a script that
    bypasses make, relies on."""
    monkeypatch.delenv("TENT_POLE_USE_TEST_CONFIG", raising=False)
    monkeypatch.setattr(config, "CONFIG", {"beta": True})
    assert config.use_test_config() is True


def test_use_test_config_false_when_beta_false_in_config(monkeypatch):
    monkeypatch.delenv("TENT_POLE_USE_TEST_CONFIG", raising=False)
    monkeypatch.setattr(config, "CONFIG", {"beta": False})
    assert config.use_test_config() is False


def test_use_test_config_true_when_either_env_var_or_config_set(monkeypatch):
    monkeypatch.setenv("TENT_POLE_USE_TEST_CONFIG", "1")
    monkeypatch.setattr(config, "CONFIG", {})
    assert config.use_test_config() is True


def test_config_api_url_ignores_dev_section_when_test_config_off(monkeypatch):
    monkeypatch.delenv("TENT_POLE_USE_TEST_CONFIG", raising=False)
    monkeypatch.setattr(
        config, "CONFIG",
        {"general": {"api_url": "https://ncl.instructure.com"},
         "dev": {"test_api_url": "https://ncl.beta.instructure.com"}},
    )
    assert config.config_api_url() == "https://ncl.instructure.com"


def test_config_api_url_uses_dev_section_when_test_config_on(monkeypatch):
    monkeypatch.setenv("TENT_POLE_USE_TEST_CONFIG", "1")
    monkeypatch.setattr(
        config, "CONFIG",
        {"general": {"api_url": "https://ncl.instructure.com"},
         "dev": {"test_api_url": "https://ncl.beta.instructure.com"}},
    )
    assert config.config_api_url() == "https://ncl.beta.instructure.com"


def test_config_course_uses_dev_section_when_test_config_on(monkeypatch):
    monkeypatch.setenv("TENT_POLE_USE_TEST_CONFIG", "1")
    monkeypatch.setattr(
        config, "CONFIG",
        {"course": {"identifier": "CSC1034"},
         "dev": {"test_course_id": "npl25 Personal Sandbox"}},
    )
    assert config.config_course() == "npl25 Personal Sandbox"


def test_config_api_key_uses_dev_section_when_test_config_on(monkeypatch):
    monkeypatch.setenv("TENT_POLE_USE_TEST_CONFIG", "1")
    monkeypatch.setattr(
        config, "CONFIG",
        {"general": {"api_key": "prod-key"}, "dev": {"test_api_key": "test-key"}},
    )
    assert config.config_api_key() == "test-key"


def test_config_api_key_does_not_blend_general_when_test_config_on_and_dev_unset(monkeypatch):
    ## "use the test config" means only the test config -- no silent
    ## fallback to [general] even if [dev] test_api_key is unset, unlike
    ## config_test_api_key() (used only by the pytest harness), which
    ## deliberately does fall back to [general] as a convenience.
    monkeypatch.setenv("TENT_POLE_USE_TEST_CONFIG", "1")
    monkeypatch.setattr(config, "CONFIG", {"general": {"api_key": "prod-key"}})
    assert config.config_api_key() is None


## CLI commands -- regression tests: api-key and course used to crash with
## "takes 0 positional arguments but 1 was given" (called as
## config_api_key(CONFIG)/config_course(CONFIG), but both functions take
## no arguments and read the module-level CONFIG directly).

def test_cli_api_key_does_not_crash(monkeypatch):
    monkeypatch.setattr(config, "CONFIG", {"general": {"api_key": "secret"}})
    result = CliRunner().invoke(config.config, ["api-key"])
    assert result.exit_code == 0, result.output
    assert "secret" in result.output


def test_cli_course_does_not_crash(monkeypatch):
    monkeypatch.setattr(config, "CONFIG", {"course": {"id": "12345"}})
    result = CliRunner().invoke(config.config, ["course"])
    assert result.exit_code == 0, result.output
    assert "12345" in result.output


def test_cli_dump_does_not_crash(monkeypatch):
    monkeypatch.setattr(config, "CONFIG", {"course": {"id": "12345"}})
    result = CliRunner().invoke(config.config, ["dump"])
    assert result.exit_code == 0, result.output
