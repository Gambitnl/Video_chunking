
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import json
import numpy as np
import torch

from src.diarizer import SpeakerDiarizer, SpeakerProfileManager, SpeakerSegment
from src.transcriber import TranscriptionSegment

@pytest.fixture
def diarizer():
    """Provides a SpeakerDiarizer instance."""
    return SpeakerDiarizer()

class TestSpeakerDiarizer:

    @pytest.mark.parametrize("start_a, end_a, start_b, end_b, expected_overlap", [
        (0, 10, 5, 15, 5),      # Partial overlap at the end
        (5, 15, 0, 10, 5),      # Partial overlap at the beginning
        (0, 10, 2, 8, 6),       # B is inside A
        (2, 8, 0, 10, 6),       # A is inside B
        (0, 10, 10, 20, 0),     # Adjacent, no overlap
        (0, 5, 10, 15, 0),      # No overlap
        (0, 10, 0, 10, 10),     # Exact same segment
    ])
    def test_calculate_overlap(self, diarizer, start_a, end_a, start_b, end_b, expected_overlap):
        overlap = diarizer._calculate_overlap(start_a, end_a, start_b, end_b)
        assert overlap == pytest.approx(expected_overlap)

    def test_assign_speakers_to_transcription(self, diarizer):
        trans_segments = [
            TranscriptionSegment(text="Hello", start_time=0.5, end_time=1.5),
            TranscriptionSegment(text="world", start_time=2.0, end_time=3.0),
            TranscriptionSegment(text="no speaker", start_time=10.0, end_time=11.0),
        ]
        speaker_segments = [
            SpeakerSegment(speaker_id="SPEAKER_00", start_time=0.0, end_time=1.8),
            SpeakerSegment(speaker_id="SPEAKER_01", start_time=1.9, end_time=5.0),
        ]

        enriched = diarizer.assign_speakers_to_transcription(trans_segments, speaker_segments)

        assert len(enriched) == 3
        assert enriched[0]['speaker'] == "SPEAKER_00"
        assert enriched[1]['speaker'] == "SPEAKER_01"
        assert enriched[2]['speaker'] == "UNKNOWN"

    @patch('pydub.AudioSegment')
    def test_diarize_successful_pipeline(self, MockAudioSegment, diarizer, tmp_path):
        # Mock the pipeline
        mock_pipeline_instance = MagicMock()
        mock_diarization_result = MagicMock()
        # Mock the iterable result of itertracks
        mock_diarization_result.itertracks.return_value = [
            (MagicMock(start=1.0, end=3.0), None, "SPEAKER_00"),
            (MagicMock(start=3.5, end=5.0), None, "SPEAKER_01"),
        ]
        mock_diarization_result.labels.return_value = ["SPEAKER_00", "SPEAKER_01"]

        # Mock label_timeline for each speaker
        def mock_label_timeline(speaker_id):
            if speaker_id == "SPEAKER_00":
                return [MagicMock(start=1.0, end=3.0)]
            else:
                return [MagicMock(start=3.5, end=5.0)]
        mock_diarization_result.label_timeline = mock_label_timeline

        mock_pipeline_instance.return_value = mock_diarization_result
        diarizer.pipeline = mock_pipeline_instance

        # Mock embedding model
        mock_embedding_model = MagicMock()
        mock_embedding_model.return_value = torch.tensor([[0.1, 0.2, 0.3]])
        diarizer.embedding_model = mock_embedding_model

        # Mock audio segment - this represents a non-empty audio chunk
        mock_audio_chunk = MagicMock()
        mock_audio_chunk.frame_rate = 16000
        mock_audio_chunk.__len__.return_value = 32000  # 2 seconds at 16kHz
        mock_audio_chunk.get_array_of_samples.return_value = np.zeros(16000, dtype=np.int16)

        # Set up the audio segment slicing to return chunks
        mock_full_audio = MagicMock()
        mock_full_audio.frame_rate = 16000
        mock_full_audio.__getitem__ = lambda self, key: mock_audio_chunk

        # Mock empty audio and its addition behavior
        # When we do speaker_audio += audio[segment...], it should accumulate
        accumulated_audio = MagicMock()
        accumulated_audio.frame_rate = 16000
        accumulated_audio.__len__.return_value = 32000  # Non-zero after accumulation
        accumulated_audio.get_array_of_samples.return_value = np.zeros(16000, dtype=np.int16)
        accumulated_audio.__add__ = lambda self, other: accumulated_audio
        accumulated_audio.__iadd__ = lambda self, other: accumulated_audio

        mock_empty = MagicMock()
        mock_empty.frame_rate = 16000
        mock_empty.__len__.return_value = 0
        mock_empty.__add__ = lambda self, other: accumulated_audio
        mock_empty.__iadd__ = lambda self, other: accumulated_audio

        MockAudioSegment.from_wav.return_value = mock_full_audio
        MockAudioSegment.empty.return_value = mock_empty

        from scipy.io.wavfile import write
        dummy_audio_path = tmp_path / "audio.wav"
        write(dummy_audio_path, 16000, np.zeros(16000, dtype=np.int16))

        # Act
        segments, embeddings = diarizer.diarize(dummy_audio_path)

        # Assert
        mock_pipeline_instance.assert_called_once_with(str(dummy_audio_path))
        assert len(segments) == 2
        assert segments[0].speaker_id == "SPEAKER_00"
        assert segments[0].start_time == 1.0
        assert segments[1].speaker_id == "SPEAKER_01"
        assert "SPEAKER_00" in embeddings
        assert "SPEAKER_01" in embeddings

    @patch('pyannote.audio.Pipeline.from_pretrained', side_effect=Exception("Model loading failed"))
    @patch('pydub.AudioSegment.from_file')
    def test_diarize_fallback_on_pipeline_failure(self, MockAudioSegment, MockFromPretrained, diarizer, tmp_path):
        # Arrange
        mock_audio = MagicMock()
        mock_audio.duration_seconds = 120.0
        # pydub uses len() for duration in ms
        type(mock_audio).duration_seconds = property(fget=lambda s: len(s) / 1000.0)
        mock_audio.__len__.return_value = 120000
        MockAudioSegment.return_value = mock_audio
        
        diarizer.pipeline = None # Ensure pipeline is not loaded

        dummy_audio_path = tmp_path / "audio.wav"
        dummy_audio_path.touch()

        # Act
        segments, embeddings = diarizer.diarize(dummy_audio_path)

        # Assert
        MockFromPretrained.assert_called_once()
        assert len(segments) == 1
        assert segments[0].speaker_id == "SPEAKER_00"
        assert segments[0].start_time == 0.0
        assert segments[0].end_time == 120.0

class TestSpeakerProfileManager:

    @pytest.fixture
    def profile_file(self, tmp_path):
        return tmp_path / "profiles.json"

    def test_init_no_file(self, profile_file):
        manager = SpeakerProfileManager(profile_file=profile_file)
        assert manager.profiles == {}

    def test_map_and_save_profile(self, profile_file):
        manager = SpeakerProfileManager(profile_file=profile_file)
        manager.map_speaker("session1", "SPEAKER_00", "Alice")
        manager.map_speaker("session1", "SPEAKER_01", "Bob")
        manager.map_speaker("session2", "SPEAKER_00", "Charlie")

        # Verify in-memory representation
        assert manager.profiles["session1"]["SPEAKER_00"]["name"] == "Alice"
        assert manager.profiles["session2"]["SPEAKER_00"]["name"] == "Charlie"

        # Verify file content
        with open(profile_file, 'r') as f:
            data = json.load(f)
        assert data["session1"]["SPEAKER_00"]["name"] == "Alice"

    def test_load_existing_profiles(self, profile_file):
        # Arrange: Create a profile file first
        initial_data = {"session1": {"SPEAKER_00": {"name": "Alice"}}}
        with open(profile_file, 'w') as f:
            json.dump(initial_data, f)

        # Act: Create a new manager that loads the file
        manager = SpeakerProfileManager(profile_file=profile_file)

        # Assert
        assert manager.profiles == initial_data
        name = manager.get_person_name("session1", "SPEAKER_00")
        assert name == "Alice"

    def test_get_person_name(self, profile_file):
        manager = SpeakerProfileManager(profile_file=profile_file)
        manager.map_speaker("session1", "SPEAKER_00", "Alice")

        # Test successful retrieval
        assert manager.get_person_name("session1", "SPEAKER_00") == "Alice"

        # Test unsuccessful retrievals
        assert manager.get_person_name("session1", "SPEAKER_01") is None
        assert manager.get_person_name("session2", "SPEAKER_00") is None
