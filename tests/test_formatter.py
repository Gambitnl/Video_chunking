import pytest
from src.formatter import TranscriptFormatter


@pytest.mark.parametrize("seconds, expected_timestamp", [
    (0, "00:00:00"),
    (59, "00:00:59"),
    (60, "00:01:00"),
    (3599, "00:59:59"),
    (3600, "01:00:00"),
    (86399, "23:59:59"), # 24 hours minus 1 second
])
def test_format_timestamp(seconds, expected_timestamp):
    """Test that seconds are correctly formatted into HH:MM:SS."""
    assert TranscriptFormatter.format_timestamp(seconds) == expected_timestamp
