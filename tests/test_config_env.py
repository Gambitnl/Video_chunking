import importlib
import logging
import sys


def _reload_config():
    sys.modules.pop("src.config", None)
    return importlib.import_module("src.config")


def test_invalid_int_env_value_falls_back(monkeypatch, caplog):
    monkeypatch.setenv("CHUNK_LENGTH_SECONDS", "not-a-number")

    with caplog.at_level(logging.WARNING):
        config_module = _reload_config()

    assert config_module.Config.CHUNK_LENGTH_SECONDS == 600
    warning_messages = [record.message for record in caplog.records]
    assert any("CHUNK_LENGTH_SECONDS" in message for message in warning_messages)

    monkeypatch.delenv("CHUNK_LENGTH_SECONDS", raising=False)
    _reload_config()


def test_blank_int_env_value_uses_default(monkeypatch):
    monkeypatch.setenv("CHUNK_OVERLAP_SECONDS", "")

    config_module = _reload_config()
    assert config_module.Config.CHUNK_OVERLAP_SECONDS == 10

    monkeypatch.delenv("CHUNK_OVERLAP_SECONDS", raising=False)
    _reload_config()
