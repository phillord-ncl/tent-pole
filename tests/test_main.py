from click.testing import CliRunner

from tent_pole import config
from tent_pole.main import main


def test_beta_flag_sets_use_test_config_env_var(monkeypatch):
    monkeypatch.delenv("TENT_POLE_USE_TEST_CONFIG", raising=False)
    monkeypatch.setattr(
        config, "CONFIG",
        {"general": {"api_key": "prod-key"}, "dev": {"test_api_key": "test-key"}},
    )
    result = CliRunner().invoke(main, ["--beta", "config", "api-key"])
    assert result.exit_code == 0, result.output
    assert "test-key" in result.output


def test_without_beta_flag_uses_general_config(monkeypatch):
    monkeypatch.delenv("TENT_POLE_USE_TEST_CONFIG", raising=False)
    monkeypatch.setattr(
        config, "CONFIG",
        {"general": {"api_key": "prod-key"}, "dev": {"test_api_key": "test-key"}},
    )
    result = CliRunner().invoke(main, ["config", "api-key"])
    assert result.exit_code == 0, result.output
    assert "prod-key" in result.output
