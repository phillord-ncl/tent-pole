import pytest
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


def test_fetch_config_raises_if_no_files_exist(tmp_path):
    """Known issue: fetch_config has no fallback when every candidate file
    is missing — functools.reduce over an empty list raises TypeError
    rather than returning e.g. an empty config. Documented here so the
    error-handling pass (see claude_redesign.md) has a regression test to
    fix against."""
    missing = str(tmp_path / "does-not-exist.toml")

    with pytest.raises(TypeError):
        config.fetch_config([missing])
