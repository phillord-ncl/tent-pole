import os

import canvasapi.exceptions
import pytest
from click.testing import CliRunner

from tent_pole import config, main as tp_main
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


def test_pkg_dir_prints_the_installed_package_directory():
    """What a downstream Makefile calls to find the shipped
    make-rules/ and bin/ -- must match where tent_pole itself actually
    lives, not just where main.py happens to be."""
    result = CliRunner().invoke(main, ["pkg-dir"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == os.path.dirname(tp_main.__file__)


class FakeResponse:
    def __init__(self, text):
        self.text = text


def test_cli_enriches_generic_canvas_exception(monkeypatch, capsys):
    def raise_it():
        raise canvasapi.exceptions.CanvasException(
            "Encountered an error: status code 503"
        )
    monkeypatch.setattr(tp_main, "main", raise_it)
    monkeypatch.setattr(
        config, "last_response",
        lambda: FakeResponse('{"error":"Error while uploading file"}'),
    )

    with pytest.raises(SystemExit) as excinfo:
        tp_main.cli()

    assert excinfo.value.code == 1
    stderr = capsys.readouterr().err
    assert "status code 503" in stderr
    assert "Error while uploading file" in stderr


def test_cli_generic_canvas_exception_with_no_cached_response(monkeypatch, capsys):
    """No response ever got cached (e.g. the failure was before any
    request went out at all) -- must still fail cleanly, not crash
    trying to read a response that doesn't exist."""
    def raise_it():
        raise canvasapi.exceptions.CanvasException(
            "Encountered an error: status code 503"
        )
    monkeypatch.setattr(tp_main, "main", raise_it)
    monkeypatch.setattr(config, "last_response", lambda: None)

    with pytest.raises(SystemExit) as excinfo:
        tp_main.cli()

    assert excinfo.value.code == 1
    assert "status code 503" in capsys.readouterr().err


def test_cli_does_not_duplicate_specific_canvas_exception_detail(monkeypatch, capsys):
    """BadRequest/Forbidden/etc already build their own message from
    response.text -- appending the cached response again would just
    duplicate it."""
    def raise_it():
        raise canvasapi.exceptions.BadRequest("invalid page_url parameter")
    monkeypatch.setattr(tp_main, "main", raise_it)
    monkeypatch.setattr(
        config, "last_response",
        lambda: FakeResponse("invalid page_url parameter"),
    )

    with pytest.raises(SystemExit) as excinfo:
        tp_main.cli()

    assert excinfo.value.code == 1
    stderr = capsys.readouterr().err
    assert stderr.count("invalid page_url parameter") == 1
    assert "Canvas said" not in stderr
