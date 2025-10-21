from src.formatter import sanitize_filename


def test_sanitize_filename_replaces_invalid_characters():
    raw = "Session 10/15: The Return?"
    sanitized = sanitize_filename(raw)
    assert sanitized == "Session_10_15__The_Return"
