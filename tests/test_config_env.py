import importlib
import logging
import sys
from src.config import Config


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


# Direct unit tests for get_env_as_int helper
class TestGetEnvAsInt:
    """Unit tests for Config.get_env_as_int helper method."""

    def test_valid_positive_int(self, monkeypatch):
        """Test parsing valid positive integer."""
        monkeypatch.setenv("TEST_INT", "42")
        assert Config.get_env_as_int("TEST_INT", 100) == 42

    def test_negative_int_accepted(self, monkeypatch):
        """Test that negative integers are accepted (no range validation)."""
        monkeypatch.setenv("TEST_INT", "-500")
        assert Config.get_env_as_int("TEST_INT", 100) == -500

    def test_very_large_int_accepted(self, monkeypatch):
        """Test that very large integers are accepted."""
        monkeypatch.setenv("TEST_INT", "99999999999")
        assert Config.get_env_as_int("TEST_INT", 100) == 99999999999

    def test_zero_int(self, monkeypatch):
        """Test parsing zero."""
        monkeypatch.setenv("TEST_INT", "0")
        assert Config.get_env_as_int("TEST_INT", 100) == 0

    def test_invalid_int_uses_default(self, monkeypatch, caplog):
        """Test that invalid integers fall back to default with warning."""
        monkeypatch.setenv("TEST_INT", "not-a-number")
        with caplog.at_level(logging.WARNING):
            result = Config.get_env_as_int("TEST_INT", 100)
        assert result == 100
        assert any("TEST_INT" in record.message for record in caplog.records)

    def test_float_string_uses_default(self, monkeypatch, caplog):
        """Test that float-like strings fall back to default with warning."""
        monkeypatch.setenv("TEST_INT", "10.5")
        with caplog.at_level(logging.WARNING):
            result = Config.get_env_as_int("TEST_INT", 100)
        assert result == 100
        assert any("TEST_INT" in record.message for record in caplog.records)

    def test_none_value_uses_default(self, monkeypatch):
        """Test that None/unset env var uses default."""
        monkeypatch.delenv("TEST_INT", raising=False)
        assert Config.get_env_as_int("TEST_INT", 100) == 100

    def test_empty_string_uses_default(self, monkeypatch):
        """Test that empty string uses default (no warning)."""
        monkeypatch.setenv("TEST_INT", "")
        assert Config.get_env_as_int("TEST_INT", 100) == 100

    def test_whitespace_only_uses_default(self, monkeypatch):
        """Test that whitespace-only string uses default (no warning)."""
        monkeypatch.setenv("TEST_INT", "   ")
        assert Config.get_env_as_int("TEST_INT", 100) == 100

    def test_int_with_surrounding_whitespace(self, monkeypatch):
        """Test that integers with surrounding whitespace are parsed correctly."""
        monkeypatch.setenv("TEST_INT", "  42  ")
        # Note: int("  42  ") works in Python, so this should succeed
        assert Config.get_env_as_int("TEST_INT", 100) == 42


# Direct unit tests for get_env_as_bool helper
class TestGetEnvAsBool:
    """Unit tests for Config.get_env_as_bool helper method."""

    def test_true_values(self, monkeypatch):
        """Test various truthy string values."""
        true_values = ["1", "true", "True", "TRUE", "yes", "Yes", "YES", "on", "On", "ON"]
        for value in true_values:
            monkeypatch.setenv("TEST_BOOL", value)
            assert Config.get_env_as_bool("TEST_BOOL", False) is True, f"Failed for value: {value}"

    def test_false_values(self, monkeypatch):
        """Test various falsy string values."""
        false_values = ["0", "false", "False", "FALSE", "no", "No", "NO", "off", "Off", "OFF"]
        for value in false_values:
            monkeypatch.setenv("TEST_BOOL", value)
            assert Config.get_env_as_bool("TEST_BOOL", True) is False, f"Failed for value: {value}"

    def test_unrecognized_value_is_false(self, monkeypatch):
        """Test that unrecognized values are treated as False."""
        monkeypatch.setenv("TEST_BOOL", "maybe")
        assert Config.get_env_as_bool("TEST_BOOL", True) is False

    def test_none_value_uses_default(self, monkeypatch):
        """Test that None/unset env var uses default."""
        monkeypatch.delenv("TEST_BOOL", raising=False)
        assert Config.get_env_as_bool("TEST_BOOL", True) is True
        assert Config.get_env_as_bool("TEST_BOOL", False) is False

    def test_empty_string_uses_default(self, monkeypatch):
        """Test that empty string uses default (consistent with int helper)."""
        monkeypatch.setenv("TEST_BOOL", "")
        assert Config.get_env_as_bool("TEST_BOOL", True) is True
        assert Config.get_env_as_bool("TEST_BOOL", False) is False

    def test_whitespace_only_uses_default(self, monkeypatch):
        """Test that whitespace-only string uses default (consistent with int helper)."""
        monkeypatch.setenv("TEST_BOOL", "   ")
        assert Config.get_env_as_bool("TEST_BOOL", True) is True
        assert Config.get_env_as_bool("TEST_BOOL", False) is False

    def test_bool_with_surrounding_whitespace(self, monkeypatch):
        """Test that bool values with surrounding whitespace are parsed correctly."""
        monkeypatch.setenv("TEST_BOOL", "  true  ")
        assert Config.get_env_as_bool("TEST_BOOL", False) is True

        monkeypatch.setenv("TEST_BOOL", "  false  ")
        assert Config.get_env_as_bool("TEST_BOOL", True) is False
