
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import json
import numpy as np
import torch
import sys
from types import SimpleNamespace

from src.diarizer import SpeakerDiarizer, SpeakerProfileManager, SpeakerSegment, DiarizerFactory, HuggingFaceApiDiarizer
from src.transcriber import TranscriptionSegment
from src.config import Config

@pytest.fixture
def diarizer():
    """Provides a SpeakerDiarizer instance."""
    return SpeakerDiarizer()

class TestSpeakerDiarizer:

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

    def test_embedding_to_numpy_handles_tensor_and_numpy(self, diarizer):
        tensor = torch.tensor([[0.1, 0.2, 0.3]], dtype=torch.float32)
        tensor_result = diarizer._embedding_to_numpy(tensor)
        assert isinstance(tensor_result, np.ndarray)
        assert tensor_result.shape == (3,)
        assert np.allclose(tensor_result, [0.1, 0.2, 0.3])

        wrapper = SimpleNamespace(data=np.array([[0.4, 0.5, 0.6]], dtype=np.float32))
        numpy_result = diarizer._embedding_to_numpy(wrapper)
        assert numpy_result.shape == (3,)
        assert np.allclose(numpy_result, [0.4, 0.5, 0.6])

        class DummyEmbedding:
            def numpy(self):
                return np.array([[0.7, 0.8]], dtype=np.float32)

        dummy_result = diarizer._embedding_to_numpy(DummyEmbedding())
        assert dummy_result.shape == (2,)
        assert np.allclose(dummy_result, [0.7, 0.8])

    def test_run_embedding_inference_falls_back_to_cpu(self, diarizer):
        mock_model = MagicMock()
        mock_model.to.return_value = mock_model
        mock_model.side_effect = [
            RuntimeError("CUDA error: an illegal memory access was encountered"),
            torch.tensor([[0.5, 0.1]], dtype=torch.float32)
        ]
        diarizer.embedding_model = mock_model
        diarizer.embedding_device = "cuda"
        waveform = torch.zeros((1, 10), dtype=torch.float32)

        result = diarizer._run_embedding_inference(waveform, 16000)

        assert torch.allclose(result, torch.tensor([[0.5, 0.1]], dtype=torch.float32))
        assert diarizer.embedding_device == "cpu"
        assert mock_model.call_count == 2

    @patch('pydub.AudioSegment')
    @patch.dict('sys.modules', {'torchaudio': None})
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
        mock_pipeline_instance.assert_called_once()
        pipeline_input = mock_pipeline_instance.call_args[0][0]
        if isinstance(pipeline_input, dict):
            assert pipeline_input["sample_rate"] == 16000
            assert pipeline_input["waveform"].shape[0] >= 1
        else:
            assert pipeline_input == str(dummy_audio_path)
        assert len(segments) == 2
        assert segments[0].speaker_id == "SPEAKER_00"
        assert segments[0].start_time == 1.0
        assert segments[1].speaker_id == "SPEAKER_01"
        assert "SPEAKER_00" in embeddings
        assert "SPEAKER_01" in embeddings

    @patch('pydub.AudioSegment')
    @patch.dict('sys.modules', {'torchaudio': None})
    def test_diarize_embedding_failure_is_logged(self, MockAudioSegment, diarizer, tmp_path, caplog):
        mock_pipeline_instance = MagicMock()
        mock_diarization_result = MagicMock()
        mock_diarization_result.itertracks.return_value = [
            (MagicMock(start=0.0, end=1.0), None, "SPEAKER_00"),
            (MagicMock(start=1.5, end=2.5), None, "SPEAKER_01"),
        ]
        mock_diarization_result.labels.return_value = ["SPEAKER_00", "SPEAKER_01"]

        def mock_label_timeline(speaker_id):
            if speaker_id == "SPEAKER_00":
                return [MagicMock(start=0.0, end=1.0)]
            return [MagicMock(start=1.5, end=2.5)]

        mock_diarization_result.label_timeline = mock_label_timeline
        mock_pipeline_instance.return_value = mock_diarization_result
        diarizer.pipeline = mock_pipeline_instance

        failing_embedding_model = MagicMock(side_effect=RuntimeError("numpy.ndarray object has no attribute numpy"))
        diarizer.embedding_model = failing_embedding_model

        mock_audio_chunk = MagicMock()
        mock_audio_chunk.frame_rate = 16000
        mock_audio_chunk.__len__.return_value = 2000
        mock_audio_chunk.get_array_of_samples.return_value = np.zeros(16000, dtype=np.int16)

        mock_full_audio = MagicMock()
        mock_full_audio.frame_rate = 16000
        mock_full_audio.__getitem__ = lambda self, key: mock_audio_chunk

        accumulated_audio = MagicMock()
        accumulated_audio.frame_rate = 16000
        accumulated_audio.__len__.return_value = 2000
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

        dummy_audio_path = tmp_path / "audio.wav"
        dummy_audio_path.touch()

        with caplog.at_level("WARNING"):
            segments, embeddings = diarizer.diarize(dummy_audio_path)

        assert len(segments) == 2
        assert embeddings == {}
        assert "Failed to extract embedding for SPEAKER_00" in caplog.text

    @patch('pyannote.audio.Pipeline.from_pretrained', side_effect=Exception("Model loading failed"))
    @patch('pydub.AudioSegment.from_file')
    @patch.dict('sys.modules', {'torchaudio': None})
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


    def test_preflight_missing_token_warns(self, diarizer, monkeypatch):
        monkeypatch.setattr('src.diarizer.Config.HF_TOKEN', None)

        issues = diarizer.preflight_check()

        assert len(issues) == 1
        assert issues[0].severity == "warning"

    @patch('src.diarizer.HfApi', create=True)
    def test_preflight_reports_repo_access_errors(self, MockHfApi, diarizer, monkeypatch):
        monkeypatch.setattr('src.diarizer.Config.HF_TOKEN', 'hf_token')
        instance = MockHfApi.return_value
        instance.model_info.side_effect = [
            None,
            Exception("403 Client Error"),
            None,
        ]

        issues = diarizer.preflight_check()

        assert issues
        assert any("segmentation-3.0" in issue.message for issue in issues)

    @patch('pydub.AudioSegment')
    @patch.dict('sys.modules', {'torchaudio': None})
    def test_diarize_passes_num_speakers(self, MockAudioSegment, diarizer, tmp_path):
        """Test that num_speakers parameter is correctly propagated to the pipeline."""
        # Mock pipeline
        mock_pipeline_instance = MagicMock()
        # Mock result
        mock_diarization_result = MagicMock()
        mock_diarization_result.itertracks.return_value = []
        mock_diarization_result.labels.return_value = []
        mock_diarization_result.label_timeline.return_value = []
        mock_pipeline_instance.return_value = mock_diarization_result
        diarizer.pipeline = mock_pipeline_instance

        # Mock embedding model to avoid errors
        diarizer.embedding_model = MagicMock()

        # Dummy audio
        dummy_audio_path = tmp_path / "audio.wav"
        dummy_audio_path.touch()

        # Mock audio loading
        mock_audio = MagicMock()
        mock_audio.__len__.return_value = 1000
        MockAudioSegment.from_wav.return_value = mock_audio
        MockAudioSegment.empty.return_value = MagicMock()

        # Call with num_speakers
        diarizer.diarize(dummy_audio_path, num_speakers=4)

        # Verify pipeline was called with num_speakers
        call_args = mock_pipeline_instance.call_args
        assert call_args is not None, "Pipeline should have been called"

        # call_args[0] are positional, call_args[1] are kwargs
        assert call_args[1].get('num_speakers') == 4, "num_speakers=4 should be passed to pipeline"

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

class TestDiarizerFactory:
    """Test the DiarizerFactory."""

    def test_create_local_backend(self, monkeypatch):
        """Test creating a local diarizer."""
        monkeypatch.setattr(Config, 'DIARIZATION_BACKEND', 'local')
        diarizer = DiarizerFactory.create()
        assert isinstance(diarizer, SpeakerDiarizer)

    def test_create_huggingface_backend(self, monkeypatch):
        """Test creating a Hugging Face diarizer."""
        monkeypatch.setattr(Config, 'DIARIZATION_BACKEND', 'hf_api')
        diarizer = DiarizerFactory.create()
        assert isinstance(diarizer, HuggingFaceApiDiarizer)

    def test_create_unknown_backend_raises_error(self, monkeypatch):
        """Test that an unknown backend raises a ValueError."""
        monkeypatch.setattr(Config, 'DIARIZATION_BACKEND', 'unknown')
        with pytest.raises(ValueError):
            DiarizerFactory.create()

class TestExtractedMethods:
    """Test suite for extracted diarization methods."""

    @pytest.fixture
    def diarizer(self):
        """Provides a SpeakerDiarizer instance."""
        return SpeakerDiarizer()

    @pytest.fixture
    def mock_audio_segment_setup(self):
        """Provides common mock setup for pydub.AudioSegment."""
        # Mock audio chunk
        mock_audio_chunk = MagicMock()
        mock_audio_chunk.frame_rate = 16000
        mock_audio_chunk.__len__.return_value = 16000
        mock_audio_chunk.get_array_of_samples.return_value = np.zeros(16000, dtype=np.int16)

        # Mock full audio
        mock_full_audio = MagicMock()
        mock_full_audio.frame_rate = 16000
        mock_full_audio.__getitem__ = lambda self, key: mock_audio_chunk

        # Mock empty audio accumulation
        accumulated_audio = MagicMock()
        accumulated_audio.frame_rate = 16000
        accumulated_audio.__len__.return_value = 16000
        accumulated_audio.get_array_of_samples.return_value = np.zeros(16000, dtype=np.int16)
        accumulated_audio.__add__ = lambda self, other: accumulated_audio
        accumulated_audio.__iadd__ = lambda self, other: accumulated_audio

        # Mock empty audio
        mock_empty = MagicMock()
        mock_empty.frame_rate = 16000
        mock_empty.__len__.return_value = 0
        mock_empty.__add__ = lambda self, other: accumulated_audio
        mock_empty.__iadd__ = lambda self, other: accumulated_audio

        return {
            'audio_chunk': mock_audio_chunk,
            'full_audio': mock_full_audio,
            'accumulated_audio': accumulated_audio,
            'empty': mock_empty
        }

    def test_load_audio_for_diarization_with_torchaudio(self, diarizer, tmp_path, monkeypatch):
        """Test audio loading with torchaudio succeeds."""
        # Create a dummy audio file
        from scipy.io.wavfile import write
        dummy_audio_path = tmp_path / "test.wav"
        write(dummy_audio_path, 16000, np.zeros(16000, dtype=np.int16))

        # Mock torchaudio to ensure it's used
        mock_torchaudio = MagicMock()
        mock_waveform = torch.zeros((1, 16000))
        mock_torchaudio.load.return_value = (mock_waveform, 16000)

        with patch.dict('sys.modules', {'torchaudio': mock_torchaudio}):
            result = diarizer._load_audio_for_diarization(dummy_audio_path)

        # Should return dict with waveform and sample_rate
        assert isinstance(result, dict)
        assert "waveform" in result
        assert "sample_rate" in result
        assert result["sample_rate"] == 16000

    def test_load_audio_for_diarization_fallback(self, diarizer, tmp_path):
        """Test audio loading falls back to file path when torchaudio fails."""
        dummy_audio_path = tmp_path / "test.wav"
        dummy_audio_path.touch()

        # Mock torchaudio to raise an exception
        with patch.dict('sys.modules', {'torchaudio': None}):
            result = diarizer._load_audio_for_diarization(dummy_audio_path)

        # Should return string path as fallback
        assert isinstance(result, str)
        assert result == str(dummy_audio_path)

    def test_perform_diarization_returns_segments(self, diarizer):
        """Test that _perform_diarization converts pipeline results to segments."""
        # Mock pipeline result
        mock_diarization = MagicMock()
        mock_diarization.itertracks.return_value = [
            (MagicMock(start=0.0, end=2.5), None, "SPEAKER_00"),
            (MagicMock(start=2.5, end=5.0), None, "SPEAKER_01"),
            (MagicMock(start=5.0, end=7.0), None, "SPEAKER_00"),
        ]

        # Mock the pipeline
        diarizer.pipeline = MagicMock(return_value=mock_diarization)

        # Execute
        diarization_result, segments = diarizer._perform_diarization("dummy_input.wav")

        # Verify results
        assert diarization_result == mock_diarization
        assert len(segments) == 3
        assert segments[0].speaker_id == "SPEAKER_00"
        assert segments[0].start_time == 0.0
        assert segments[0].end_time == 2.5
        assert segments[1].speaker_id == "SPEAKER_01"
        assert segments[2].speaker_id == "SPEAKER_00"

    def test_perform_diarization_with_dict_input(self, diarizer):
        """Test that _perform_diarization works with dict input."""
        mock_diarization = MagicMock()
        mock_diarization.itertracks.return_value = [
            (MagicMock(start=1.0, end=3.0), None, "SPEAKER_00"),
        ]

        diarizer.pipeline = MagicMock(return_value=mock_diarization)

        dict_input = {
            "waveform": torch.zeros((1, 16000)),
            "sample_rate": 16000
        }

        diarization_result, segments = diarizer._perform_diarization(dict_input)

        assert len(segments) == 1
        diarizer.pipeline.assert_called_once_with(dict_input)

    def test_extract_speaker_embeddings_no_model(self, diarizer, tmp_path):
        """Test that embedding extraction returns empty dict when model is None."""
        diarizer.embedding_model = None
        mock_diarization = MagicMock()

        dummy_audio_path = tmp_path / "test.wav"
        dummy_audio_path.touch()

        result = diarizer._extract_speaker_embeddings(dummy_audio_path, mock_diarization)

        assert result == {}

    @patch('pydub.AudioSegment')
    def test_extract_speaker_embeddings_successful(self, MockAudioSegment, diarizer, tmp_path, mock_audio_segment_setup):
        """Test successful embedding extraction for multiple speakers."""
        # Setup
        mock_embedding_model = MagicMock()
        mock_embedding_model.return_value = torch.tensor([[0.1, 0.2, 0.3]])
        diarizer.embedding_model = mock_embedding_model

        # Use fixture for audio segment mocking
        mocks = mock_audio_segment_setup
        MockAudioSegment.from_wav.return_value = mocks['full_audio']
        MockAudioSegment.empty.return_value = mocks['empty']

        # Mock diarization result
        mock_diarization = MagicMock()
        mock_diarization.labels.return_value = ["SPEAKER_00", "SPEAKER_01"]

        def mock_label_timeline(speaker_id):
            return [MagicMock(start=0.0, end=2.0)]

        mock_diarization.label_timeline = mock_label_timeline

        dummy_audio_path = tmp_path / "test.wav"
        dummy_audio_path.touch()

        # Execute
        embeddings = diarizer._extract_speaker_embeddings(dummy_audio_path, mock_diarization)

        # Verify
        assert "SPEAKER_00" in embeddings
        assert "SPEAKER_01" in embeddings
        assert isinstance(embeddings["SPEAKER_00"], np.ndarray)
        assert isinstance(embeddings["SPEAKER_01"], np.ndarray)

    @patch('pydub.AudioSegment')
    def test_extract_speaker_embeddings_skips_empty_segments(self, MockAudioSegment, diarizer, tmp_path):
        """Test that embedding extraction skips speakers with no audio."""
        mock_embedding_model = MagicMock()
        diarizer.embedding_model = mock_embedding_model

        # Mock empty audio segment
        mock_empty = MagicMock()
        mock_empty.frame_rate = 16000
        mock_empty.__len__.return_value = 0

        mock_full_audio = MagicMock()
        mock_full_audio.frame_rate = 16000

        MockAudioSegment.from_wav.return_value = mock_full_audio
        MockAudioSegment.empty.return_value = mock_empty

        mock_diarization = MagicMock()
        mock_diarization.labels.return_value = ["SPEAKER_00"]
        mock_diarization.label_timeline.return_value = [MagicMock(start=0.0, end=0.0)]

        dummy_audio_path = tmp_path / "test.wav"
        dummy_audio_path.touch()

        embeddings = diarizer._extract_speaker_embeddings(dummy_audio_path, mock_diarization)

        # Should be empty since audio segment was empty
        assert embeddings == {}
        # Embedding model should not be called
        mock_embedding_model.assert_not_called()

    def test_extract_speaker_embeddings_handles_pydub_import_error(self, diarizer, tmp_path):
        """Test that embedding extraction handles pydub import failure gracefully."""
        diarizer.embedding_model = MagicMock()

        with patch.dict('sys.modules', {'pydub': None}):
            with patch('builtins.__import__', side_effect=ImportError("pydub not found")):
                mock_diarization = MagicMock()
                dummy_audio_path = tmp_path / "test.wav"

                embeddings = diarizer._extract_speaker_embeddings(dummy_audio_path, mock_diarization)

                assert embeddings == {}

    @patch('pydub.AudioSegment')
    def test_extract_speaker_embeddings_handles_audio_load_error(self, MockAudioSegment, diarizer, tmp_path):
        """Test that embedding extraction handles audio loading errors."""
        diarizer.embedding_model = MagicMock()
        MockAudioSegment.from_wav.side_effect = Exception("Audio file corrupt")

        mock_diarization = MagicMock()
        dummy_audio_path = tmp_path / "test.wav"
        dummy_audio_path.touch()

        embeddings = diarizer._extract_speaker_embeddings(dummy_audio_path, mock_diarization)

        assert embeddings == {}

    @patch('pydub.AudioSegment')
    def test_extract_speaker_embeddings_handles_inference_error(self, MockAudioSegment, diarizer, tmp_path, caplog, mock_audio_segment_setup):
        """Test that embedding extraction continues when inference fails for one speaker."""
        # Setup: first speaker succeeds, second fails
        mock_embedding_model = MagicMock()
        mock_embedding_model.side_effect = [
            torch.tensor([[0.1, 0.2]]),  # Success for SPEAKER_00
            RuntimeError("Inference failed"),  # Failure for SPEAKER_01
        ]
        diarizer.embedding_model = mock_embedding_model

        # Use fixture for audio segment mocking
        mocks = mock_audio_segment_setup
        MockAudioSegment.from_wav.return_value = mocks['full_audio']
        MockAudioSegment.empty.return_value = mocks['empty']

        mock_diarization = MagicMock()
        mock_diarization.labels.return_value = ["SPEAKER_00", "SPEAKER_01"]
        mock_diarization.label_timeline.return_value = [MagicMock(start=0.0, end=1.0)]

        dummy_audio_path = tmp_path / "test.wav"
        dummy_audio_path.touch()

        with caplog.at_level("WARNING"):
            embeddings = diarizer._extract_speaker_embeddings(dummy_audio_path, mock_diarization)

        # Should have SPEAKER_00 but not SPEAKER_01
        assert "SPEAKER_00" in embeddings
        assert "SPEAKER_01" not in embeddings
        assert "Failed to extract embedding for SPEAKER_01" in caplog.text

    @patch('pydub.AudioSegment')
    def test_load_audio_for_embeddings_success(self, MockAudioSegment, diarizer, tmp_path):
        """Test successful audio loading for embeddings."""
        mock_audio = MagicMock()
        mock_audio.__len__.return_value = 32000  # 32 seconds in ms
        MockAudioSegment.from_wav.return_value = mock_audio

        dummy_audio_path = tmp_path / "test.wav"
        dummy_audio_path.touch()

        result = diarizer._load_audio_for_embeddings(dummy_audio_path)

        assert result is not None
        assert result == mock_audio
        MockAudioSegment.from_wav.assert_called_once_with(str(dummy_audio_path))

    def test_load_audio_for_embeddings_pydub_import_error(self, diarizer, tmp_path):
        """Test that _load_audio_for_embeddings handles pydub import failure."""
        with patch.dict('sys.modules', {'pydub': None}):
            with patch('builtins.__import__', side_effect=ImportError("pydub not found")):
                dummy_audio_path = tmp_path / "test.wav"
                result = diarizer._load_audio_for_embeddings(dummy_audio_path)

                assert result is None

    @patch('pydub.AudioSegment')
    def test_load_audio_for_embeddings_file_load_error(self, MockAudioSegment, diarizer, tmp_path):
        """Test that _load_audio_for_embeddings handles file loading errors."""
        MockAudioSegment.from_wav.side_effect = Exception("File not found")

        dummy_audio_path = tmp_path / "test.wav"
        result = diarizer._load_audio_for_embeddings(dummy_audio_path)

        assert result is None

    @patch('pydub.AudioSegment')
    def test_extract_single_speaker_embedding_success(self, MockAudioSegment, diarizer, mock_audio_segment_setup):
        """Test successful single speaker embedding extraction."""
        # Setup mocks
        mock_embedding_model = MagicMock()
        mock_embedding_model.return_value = torch.tensor([[0.1, 0.2, 0.3]])
        diarizer.embedding_model = mock_embedding_model

        mocks = mock_audio_segment_setup
        mock_audio = mocks['full_audio']
        MockAudioSegment.empty.return_value = mocks['empty']

        # Mock diarization result
        mock_diarization = MagicMock()
        mock_diarization.label_timeline.return_value = [
            MagicMock(start=0.0, end=2.0),
            MagicMock(start=3.0, end=5.0)
        ]

        # Execute
        embedding = diarizer._extract_single_speaker_embedding(
            "SPEAKER_00", mock_diarization, mock_audio
        )

        # Verify
        assert embedding is not None
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (3,)
        mock_embedding_model.assert_called_once()

    @patch('pydub.AudioSegment')
    def test_extract_single_speaker_embedding_no_audio(self, MockAudioSegment, diarizer):
        """Test that _extract_single_speaker_embedding returns None when no audio."""
        # Mock empty audio segment
        mock_empty = MagicMock()
        mock_empty.__len__.return_value = 0
        MockAudioSegment.empty.return_value = mock_empty

        mock_audio = MagicMock()
        mock_diarization = MagicMock()
        mock_diarization.label_timeline.return_value = []

        embedding = diarizer._extract_single_speaker_embedding(
            "SPEAKER_00", mock_diarization, mock_audio
        )

        assert embedding is None

    @patch('pydub.AudioSegment')
    def test_extract_single_speaker_embedding_inference_error(self, MockAudioSegment, diarizer, mock_audio_segment_setup):
        """Test that _extract_single_speaker_embedding propagates inference errors."""
        # Setup failing embedding model
        mock_embedding_model = MagicMock()
        mock_embedding_model.side_effect = RuntimeError("Inference failed")
        diarizer.embedding_model = mock_embedding_model

        mocks = mock_audio_segment_setup
        mock_audio = mocks['full_audio']
        MockAudioSegment.empty.return_value = mocks['empty']

        mock_diarization = MagicMock()
        mock_diarization.label_timeline.return_value = [MagicMock(start=0.0, end=1.0)]

        # Should raise the inference error
        with pytest.raises(RuntimeError, match="Inference failed"):
            diarizer._extract_single_speaker_embedding(
                "SPEAKER_00", mock_diarization, mock_audio
            )

class TestHuggingFaceApiDiarizer:
    """Test the HuggingFaceApiDiarizer."""

    def test_diarize_no_hf_token_raises_error(self, monkeypatch):
        """Test that diarize raises an error if HF_TOKEN is not set."""
        monkeypatch.setattr(Config, 'HF_TOKEN', None)
        diarizer = HuggingFaceApiDiarizer()
        with pytest.raises(ValueError):
            diarizer.diarize(Path("test.wav"))
