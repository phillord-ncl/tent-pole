import os

import toml

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


def test_ancestor_config_paths_root_most_first(tmp_path):
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)

    paths = config.ancestor_config_paths(str(deep))
    dirs = [os.path.dirname(p) for p in paths]

    assert all(p.endswith("tent-pole.toml") for p in paths)
    assert dirs[0] == os.path.abspath(os.sep)  # filesystem root first
    assert dirs[-1] == str(deep)  # most specific (start_dir) last
    # an unbroken parent-to-child chain, each dir the direct parent of the next
    for parent, child in zip(dirs, dirs[1:]):
        assert os.path.dirname(child) == parent
    assert len(dirs) == len(set(dirs))  # no duplicates


def test_cascade_lets_a_repo_root_config_apply_to_a_subdirectory(tmp_path):
    """The actual motivating case: a course-id set once at a course repo's
    root should apply to every subproject directory beneath it, without
    repeating it in each one."""
    root = tmp_path / "course-repo"
    sub = root / "project-1"
    sub.mkdir(parents=True)
    write_toml(root / "tent-pole.toml", {"course": {"id": "12345"}})

    merged = config.fetch_config(config.ancestor_config_paths(str(sub)))

    assert merged["course"]["id"] == "12345"


def test_subdirectory_config_overrides_repo_root_on_conflict(tmp_path):
    root = tmp_path / "course-repo"
    sub = root / "project-1"
    sub.mkdir(parents=True)
    write_toml(root / "tent-pole.toml", {"course": {"id": "12345"}})
    write_toml(sub / "tent-pole.toml", {"course": {"id": "OVERRIDE"}})

    merged = config.fetch_config(config.ancestor_config_paths(str(sub)))

    assert merged["course"]["id"] == "OVERRIDE"


def test_config_api_url_falls_back_to_default(monkeypatch):
    monkeypatch.setattr(config, "CONFIG", {})
    assert config.config_api_url() == config.DEFAULT_API_URL


def test_config_api_url_uses_configured_value(monkeypatch):
    monkeypatch.setattr(
        config, "CONFIG", {"general": {"api_url": "https://ncl.beta.instructure.com"}}
    )
    assert config.config_api_url() == "https://ncl.beta.instructure.com"
