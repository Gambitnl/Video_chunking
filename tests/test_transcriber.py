import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import numpy as np

# Mock the config before other imports to ensure it's applied
@pytest.fixture(autouse=True)
def mock_config():
    with patch('src.transcriber.Config') as MockConfig:
        MockConfig.WHISPER_BACKEND = 'local'
        MockConfig.WHISPER_MODEL = 'tiny'
        MockConfig.GROQ_API_KEY = 'test-groq-api-key'
        yield MockConfig

from src.transcriber import (
    TranscriberFactory,
    FasterWhisperTranscriber,
    GroqTranscriber,
    BaseTranscriber,
    ChunkTranscription,
    TranscriptionSegment
)
from src.chunker import AudioChunk

@pytest.fixture
def dummy_audio_chunk():
    """Provides a dummy AudioChunk for testing."""
    return AudioChunk(
        chunk_index=0,
        audio=np.zeros(16000, dtype=np.float32),
        start_time=10.0,
        end_time=20.0,
        sample_rate=16000
    )

class TestTranscriberFactory:
    def test_create_local_backend(self, mock_config):
        mock_config.WHISPER_BACKEND = 'local'
        transcriber = TranscriberFactory.create()
        assert isinstance(transcriber, FasterWhisperTranscriber)

    def test_create_groq_backend(self, mock_config):
        mock_config.WHISPER_BACKEND = 'groq'
        transcriber = TranscriberFactory.create()
        assert isinstance(transcriber, GroqTranscriber)

    def test_create_unknown_backend_raises_error(self):
        with pytest.raises(ValueError, match="Unknown transcriber backend: unknown"):
            TranscriberFactory.create(backend='unknown')

    def test_create_openai_backend_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            TranscriberFactory.create(backend='openai')

    def test_create_groq_with_no_api_key_raises_error(self, mock_config):
        mock_config.GROQ_API_KEY = None
        with pytest.raises(ValueError, match="Groq API key required"):
            TranscriberFactory.create(backend='groq')

@patch('faster_whisper.WhisperModel')
def test_faster_whisper_transcriber(MockWhisperModel, dummy_audio_chunk):
    """Tests the FasterWhisperTranscriber logic."""
    # Arrange: Mock the faster_whisper model and its transcribe method
    mock_model_instance = MockWhisperModel.return_value
    
    # Mock segment objects that the real library would return
    MockSegment = MagicMock()
    MockSegment.start = 1.0
    MockSegment.end = 3.0
    MockSegment.text = " Hello world "
    MockSegment.avg_logprob = -0.5
    MockSegment.words = [
        MagicMock(word='Hello', start=1.0, end=1.5, probability=0.9),
        MagicMock(word='world', start=1.6, end=2.0, probability=0.8)
    ]

    mock_info = MagicMock()
    mock_info.language = 'nl'
    mock_model_instance.transcribe.return_value = ([MockSegment], mock_info)

    transcriber = FasterWhisperTranscriber(model_name='test_model')
    
    # Act
    result = transcriber.transcribe_chunk(dummy_audio_chunk, language='nl')

    # Assert
    mock_model_instance.transcribe.assert_called_once()
    assert isinstance(result, ChunkTranscription)
    assert result.language == 'nl'
    assert len(result.segments) == 1

    segment = result.segments[0]
    assert segment.text == "Hello world"
    assert segment.start_time == pytest.approx(10.0 + 1.0)
    assert segment.end_time == pytest.approx(10.0 + 3.0)
    assert segment.confidence == -0.5
    
    assert len(segment.words) == 2
    assert segment.words[0]['word'] == 'Hello'
    assert segment.words[0]['start'] == pytest.approx(10.0 + 1.0)

@patch('groq.Groq')
@patch('soundfile.write')
@patch('builtins.open', new_callable=mock_open)
@patch('pathlib.Path.unlink')
@patch('pathlib.Path.exists', return_value=True)
def test_groq_transcriber(mock_path_exists, mock_unlink, mock_file_open, mock_sf_write, MockGroq, dummy_audio_chunk):
    """Tests the GroqTranscriber logic with extensive mocking."""
    # Arrange: Mock the Groq client and its API response
    mock_groq_client = MockGroq.return_value
    mock_response = MagicMock()
    mock_response.language = 'nl'
    mock_response.segments = [
        {'start': 1.0, 'end': 3.0, 'text': ' Groq transcription '}
    ]
    mock_response.words = [
        {'word': 'Groq', 'start': 1.0, 'end': 1.5},
        {'word': 'transcription', 'start': 1.6, 'end': 2.8}
    ]
    mock_groq_client.audio.transcriptions.create.return_value = mock_response

    transcriber = GroqTranscriber(api_key='fake-key')

    # Act
    result = transcriber.transcribe_chunk(dummy_audio_chunk, language='nl')

    # Assert
    # Verify a temporary file was written and then opened
    mock_sf_write.assert_called_once()
    mock_file_open.assert_called_with(mock_sf_write.call_args[0][0], 'rb')

    # Verify the API was called
    mock_groq_client.audio.transcriptions.create.assert_called_once()

    # Verify the temporary file was cleaned up
    mock_unlink.assert_called_once()

    # Verify the returned data structure
    assert isinstance(result, ChunkTranscription)
    assert result.language == 'nl'
    assert len(result.segments) == 1

    segment = result.segments[0]
    assert segment.text == "Groq transcription"
    assert segment.start_time == pytest.approx(10.0 + 1.0)
    assert segment.end_time == pytest.approx(10.0 + 3.0)
    
    assert len(segment.words) == 2
    assert segment.words[0]['word'] == 'Groq'
    assert segment.words[1]['start'] == pytest.approx(10.0 + 1.6)