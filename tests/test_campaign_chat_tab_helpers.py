import types

from src.ui.campaign_chat_tab import (
    describe_llm_configuration,
    format_character_counter,
    reset_character_counter,
)
from src.ui.constants import StatusIndicators as SI


def test_format_character_counter_within_limit():
    result = format_character_counter("hello", max_length=10)
    assert result == f"{SI.INFO} 5 / 10 characters (5 characters remaining)"


def test_format_character_counter_over_limit():
    result = format_character_counter("abcdefghijk", max_length=10)
    assert result == f"{SI.INFO} 11 / 10 characters (longer messages are trimmed to the limit)"


def test_reset_character_counter_uses_zero_length():
    assert reset_character_counter().startswith(f"{SI.INFO} 0 /")


def test_describe_llm_configuration_includes_provider_and_model():
    chat_client = types.SimpleNamespace(llm_provider="openai", model_name="gpt-4")
    summary = describe_llm_configuration(chat_client)
    assert "openai" in summary
    assert "gpt-4" in summary


def test_describe_llm_configuration_handles_missing_client():
    summary = describe_llm_configuration(None)
    assert SI.WARNING in summary
