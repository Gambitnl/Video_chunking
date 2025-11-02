
import pytest
from unittest.mock import MagicMock, patch
from src.pipeline import DDSessionProcessor
from src.chunker import AudioChunk

@patch('src.pipeline.TranscriberFactory.create')
def test_language_is_passed_to_processor(mock_create_transcriber):
    """Test that the language parameter is correctly passed to the processor."""
    mock_transcriber = MagicMock()
    mock_create_transcriber.return_value = mock_transcriber

    processor = DDSessionProcessor(session_id="test_session", language="nl")
    assert processor.language == "nl"
