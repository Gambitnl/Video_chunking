"""
Test suite for src/chunker.py

Priority: P0 - Critical
Estimated Effort: 1 day
Status: Template - Not Implemented

See docs/TEST_PLANS.md for detailed specifications.
"""
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from src.chunker import HybridChunker, AudioChunk
from src.config import Config


# ============================================================================
# AudioChunk Dataclass Tests
# ============================================================================

class TestAudioChunk:
    """Test AudioChunk dataclass."""

    def test_audio_chunk_duration_property(self):
        """Test duration property calculation."""
        chunk = AudioChunk(
            audio=np.zeros(16000),
            start_time=10.0,
            end_time=11.0,
            sample_rate=16000,
            chunk_index=0
        )
        assert chunk.duration == 1.0

    def test_audio_chunk_attributes(self):
        """Test all attributes are accessible."""
        audio_data = np.zeros(32000)
        chunk = AudioChunk(
            audio=audio_data,
            start_time=5.0,
            end_time=7.0,
            sample_rate=16000,
            chunk_index=3
        )

        assert chunk.start_time == 5.0
        assert chunk.end_time == 7.0
        assert chunk.sample_rate == 16000
        assert chunk.chunk_index == 3
        assert len(chunk.audio) == 32000

    def test_audio_chunk_to_dict(self):
        """Test to_dict method of AudioChunk."""
        audio_data = np.zeros(16000)
        chunk = AudioChunk(
            audio=audio_data,
            start_time=10.0,
            end_time=11.0,
            sample_rate=16000,
            chunk_index=0
        )
        expected_dict = {
            "start_time": 10.0,
            "end_time": 11.0,
            "sample_rate": 16000,
            "chunk_index": 0,
        }
        assert chunk.to_dict() == expected_dict

    def test_audio_chunk_from_dict(self):
        """Test from_dict method of AudioChunk with audio data."""
        chunk_data = {
            "start_time": 10.0,
            "end_time": 11.0,
            "sample_rate": 16000,
            "chunk_index": 0,
        }
        dummy_audio = np.array([1.0, 2.0, 3.0])
        chunk = AudioChunk.from_dict(chunk_data, audio_data=dummy_audio)

        assert chunk.start_time == 10.0
        assert chunk.end_time == 11.0
        assert chunk.sample_rate == 16000
        assert chunk.chunk_index == 0
        assert np.array_equal(chunk.audio, dummy_audio)

    def test_audio_chunk_from_dict_no_audio_data(self):
        """Test from_dict method of AudioChunk without audio data."""
        chunk_data = {
            "start_time": 10.0,
            "end_time": 11.0,
            "sample_rate": 16000,
            "chunk_index": 0,
        }
        chunk = AudioChunk.from_dict(chunk_data)

        assert chunk.start_time == 10.0
        assert chunk.end_time == 11.0
        assert chunk.sample_rate == 16000
        assert chunk.chunk_index == 0
        assert np.array_equal(chunk.audio, np.array([]))


# ============================================================================
# Initialization Tests
# ============================================================================

class TestHybridChunkerInit:
    """Test initialization of HybridChunker."""

    def test_init_with_defaults(self):
        """Test initialization with default config values."""
        # Mock torch.hub.load to avoid downloading VAD model
        mock_model = Mock()
        mock_utils = [Mock()]  # get_speech_timestamps

        with patch('torch.hub.load', return_value=(mock_model, mock_utils)):
            chunker = HybridChunker()
            assert chunker.max_chunk_length == Config.CHUNK_LENGTH_SECONDS
            assert chunker.overlap_length == Config.CHUNK_OVERLAP_SECONDS
            assert chunker.vad_threshold == 0.5
            assert chunker.vad_model is not None
            assert chunker.get_speech_timestamps is not None

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        mock_model = Mock()
        mock_utils = [Mock()]

        with patch('torch.hub.load', return_value=(mock_model, mock_utils)):
            chunker = HybridChunker(
                max_chunk_length=300,
                overlap_length=5,
                vad_threshold=0.7
            )
            assert chunker.max_chunk_length == 300
            assert chunker.overlap_length == 5
            assert chunker.vad_threshold == 0.7

    def test_init_loads_vad_model(self):
        """Test that Silero VAD model is loaded during init."""
        mock_model = Mock()
        mock_utils = [Mock()]

        with patch('torch.hub.load', return_value=(mock_model, mock_utils)) as mock_load:
            chunker = HybridChunker()

            # Verify torch.hub.load was called with correct parameters
            mock_load.assert_called_once_with(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )

            # Verify model and utils are assigned
            assert chunker.vad_model == mock_model
            assert chunker.get_speech_timestamps == mock_utils[0]


# ============================================================================
# Chunking Logic Tests
# ============================================================================

class TestHybridChunkerChunking:
    """Test core chunking functionality."""

    def test_chunk_audio_basic(self, tmp_path):
        """Test basic chunking of audio file."""
        # Create mock audio (16kHz, 30 seconds)
        audio_path = create_test_audio(tmp_path, duration=30, sample_rate=16000)

        # Mock VAD model
        mock_model = Mock()
        mock_get_speech_timestamps = Mock(return_value=[])  # No speech segments

        with patch('torch.hub.load', return_value=(mock_model, [mock_get_speech_timestamps])):
            chunker = HybridChunker(max_chunk_length=10, overlap_length=2)
            chunks = chunker.chunk_audio(audio_path)

            # Should create 3-4 chunks from 30 seconds
            # Chunk 1: 0-10s, Chunk 2: 8-18s, Chunk 3: 16-26s, Chunk 4: 24-30s
            assert len(chunks) >= 3
            assert len(chunks) <= 4

            # Verify all are AudioChunk instances
            for chunk in chunks:
                assert isinstance(chunk, AudioChunk)
                assert chunk.sample_rate == 16000

    def test_chunk_audio_creates_overlap(self, tmp_path):
        """Test that chunks have correct overlap."""
        # Create 100s audio
        audio_path = create_test_audio(tmp_path, duration=100, sample_rate=16000)

        # Mock VAD model
        mock_model = Mock()
        mock_get_speech_timestamps = Mock(return_value=[])

        with patch('torch.hub.load', return_value=(mock_model, [mock_get_speech_timestamps])):
            chunker = HybridChunker(max_chunk_length=30, overlap_length=5)
            chunks = chunker.chunk_audio(audio_path)

            # Verify overlap between consecutive chunks
            # chunk[i].end_time - overlap ≈ chunk[i+1].start_time
            for i in range(len(chunks) - 1):
                expected_next_start = chunks[i].end_time - chunker.overlap_length
                actual_next_start = chunks[i + 1].start_time
                assert abs(expected_next_start - actual_next_start) < 0.1, \
                    f"Chunk {i} overlap incorrect: expected {expected_next_start}, got {actual_next_start}"

    def test_chunk_audio_respects_max_length(self, tmp_path):
        """Test that chunks don't exceed max_chunk_length."""
        # Create 300s audio
        audio_path = create_test_audio(tmp_path, duration=300, sample_rate=16000)

        # Mock VAD model
        mock_model = Mock()
        mock_get_speech_timestamps = Mock(return_value=[])

        with patch('torch.hub.load', return_value=(mock_model, [mock_get_speech_timestamps])):
            chunker = HybridChunker(max_chunk_length=60, overlap_length=5)
            chunks = chunker.chunk_audio(audio_path)

            # Verify all chunks <= max_chunk_length + overlap
            # (overlap is added at the beginning of subsequent chunks)
            for chunk in chunks:
                # Allow slight tolerance for floating point
                assert chunk.duration <= chunker.max_chunk_length + 0.1, \
                    f"Chunk {chunk.chunk_index} duration {chunk.duration} exceeds max {chunker.max_chunk_length}"

    def test_chunk_audio_with_short_file(self, tmp_path):
        """Test chunking of audio shorter than max_chunk_length."""
        # Create 5s audio
        audio_path = create_test_audio(tmp_path, duration=5, sample_rate=16000)

        # Mock VAD model
        mock_model = Mock()
        mock_get_speech_timestamps = Mock(return_value=[])

        with patch('torch.hub.load', return_value=(mock_model, [mock_get_speech_timestamps])):
            chunker = HybridChunker(max_chunk_length=60, overlap_length=5)
            chunks = chunker.chunk_audio(audio_path)

            # Should return single chunk
            assert len(chunks) == 1
            assert chunks[0].start_time == 0.0
            assert abs(chunks[0].end_time - 5.0) < 0.1  # Allow for float precision


# ============================================================================
# VAD Detection Tests
# ============================================================================

class TestHybridChunkerVAD:
    """Test Voice Activity Detection integration."""

    def test_find_best_split_point_with_silence(self):
        """Test finding split point when silence exists."""
        # Create chunker with mocked VAD
        mock_model = Mock()
        mock_utils = [Mock()]

        with patch('torch.hub.load', return_value=(mock_model, mock_utils)):
            chunker = HybridChunker()

            # Speech segments with gaps (start, end)
            # Speech at 0-100s, gap 100-110s, speech 110-200s, gap 200-205s, speech 205-400s
            speech_segments = [
                (0.0, 100.0),
                (110.0, 200.0),
                (205.0, 400.0)
            ]

            # Target split at 150s, search window ±30s
            ideal_end = 150.0
            chunk_start = 0.0

            # Should find gap at 200-205s (end at 205s) as it's closer to target than 100-110s
            best_split = chunker._find_best_pause(speech_segments, ideal_end, chunk_start)

            # Should pick the gap ending at 110s or 205s depending on proximity and width
            # Gap at 110 is 10s wide, distance from ideal = 40s
            # Gap at 205 is 5s wide, distance from ideal = 55s
            # Score for 110: 40 - (10*2) = 20
            # Score for 205: 55 - (5*2) = 45
            # Lower score wins, so should pick 110
            assert best_split == 110.0

    def test_find_best_split_point_no_silence(self):
        """Test split point when no silence in search window."""
        mock_model = Mock()
        mock_utils = [Mock()]

        with patch('torch.hub.load', return_value=(mock_model, mock_utils)):
            chunker = HybridChunker()

            # Continuous speech - no gaps
            speech_segments = [
                (0.0, 300.0)
            ]

            ideal_end = 150.0
            chunk_start = 0.0

            # Should fall back to target time when no gaps found
            best_split = chunker._find_best_pause(speech_segments, ideal_end, chunk_start)
            assert best_split == ideal_end

    def test_proximity_scoring(self):
        """Test that proximity scoring favors gaps near target."""
        mock_model = Mock()
        mock_utils = [Mock()]

        with patch('torch.hub.load', return_value=(mock_model, mock_utils)):
            chunker = HybridChunker()

            # Two gaps of same width but different distances from target
            # Gap 1: 95-100s (ends at 100s, distance from 150 = 50s)
            # Gap 2: 145-150s (ends at 150s, distance from 150 = 0s)
            speech_segments = [
                (0.0, 95.0),
                (100.0, 145.0),
                (150.0, 300.0)
            ]

            ideal_end = 150.0
            chunk_start = 0.0

            # Should pick the gap closer to target (ending at 150s)
            best_split = chunker._find_best_pause(speech_segments, ideal_end, chunk_start)
            assert best_split == 150.0

    def test_width_scoring(self):
        """Test that wider gaps score higher."""
        mock_model = Mock()
        mock_utils = [Mock()]

        with patch('torch.hub.load', return_value=(mock_model, mock_utils)):
            chunker = HybridChunker()

            # Two gaps at similar distances from target but different widths
            # Gap 1: 145-147s (width=2s, ends at 147s, distance from 150 = 3s)
            # Gap 2: 151-161s (width=10s, ends at 161s, distance from 150 = 11s)
            speech_segments = [
                (0.0, 145.0),
                (147.0, 151.0),
                (161.0, 300.0)
            ]

            ideal_end = 150.0
            chunk_start = 0.0

            # Score for gap 1 (ends at 147): distance=3, width=2, score=3-(2*2)=-1
            # Score for gap 2 (ends at 161): distance=11, width=10, score=11-(10*2)=-9
            # Lower score wins, so should pick gap 2 (wider gap)
            best_split = chunker._find_best_pause(speech_segments, ideal_end, chunk_start)
            assert best_split == 161.0


# ============================================================================
# Progress Callback Tests
# ============================================================================

class TestChunkerProgressCallbacks:
    """Test progress callback functionality."""

    def test_progress_callback_called(self):
        """Test that progress callback is invoked during chunk creation."""
        chunker = HybridChunker.__new__(HybridChunker)
        chunker.max_chunk_length = 2.0
        chunker.overlap_length = 0.5
        chunker.logger = MagicMock()

        total_duration = 4.0

        def fake_best_pause(segments, ideal_end, chunk_start):
            return min(ideal_end, total_duration)

        chunker._find_best_pause = fake_best_pause

        audio = np.zeros(int(total_duration), dtype=np.float32)
        sr = 1
        calls = []

        chunks = chunker._create_chunks_with_pauses(
            audio=audio,
            sr=sr,
            speech_segments=[],
            progress_callback=lambda chunk, total: calls.append((chunk.chunk_index, total))
        )

        assert calls, "Progress callback should be invoked at least once."
        assert calls[-1][1] == total_duration
        assert len(chunks) >= 1

    def test_progress_callback_optional(self):
        """Test that callback is optional (no error if None)."""
        chunker = HybridChunker.__new__(HybridChunker)
        chunker.max_chunk_length = 2.0
        chunker.overlap_length = 0.5
        chunker.logger = MagicMock()
        chunker._find_best_pause = lambda segments, ideal_end, chunk_start: ideal_end

        audio = np.zeros(4, dtype=np.float32)
        sr = 1

        chunks = chunker._create_chunks_with_pauses(
            audio=audio,
            sr=sr,
            speech_segments=[],
            progress_callback=None
        )

        assert len(chunks) >= 1


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestChunkerEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_audio_file(self, tmp_path):
        """Test handling of empty audio file."""
        # Create 0-second audio (just a silent sample to have valid file)
        audio_path = create_test_audio(tmp_path, duration=0, sample_rate=16000)

        mock_model = Mock()
        mock_get_speech_timestamps = Mock(return_value=[])

        with patch('torch.hub.load', return_value=(mock_model, [mock_get_speech_timestamps])):
            chunker = HybridChunker()
            chunks = chunker.chunk_audio(audio_path)

            # Should return empty list or single very short chunk
            assert len(chunks) <= 1
            if len(chunks) == 1:
                assert chunks[0].duration < 1.0

    def test_audio_exact_chunk_length(self, tmp_path):
        """Test audio file that is exactly max_chunk_length."""
        # Create 60s audio with max_chunk_length=60
        audio_path = create_test_audio(tmp_path, duration=60, sample_rate=16000)

        mock_model = Mock()
        mock_get_speech_timestamps = Mock(return_value=[])

        with patch('torch.hub.load', return_value=(mock_model, [mock_get_speech_timestamps])):
            chunker = HybridChunker(max_chunk_length=60, overlap_length=5)
            chunks = chunker.chunk_audio(audio_path)

            # Should return single chunk
            assert len(chunks) == 1
            assert chunks[0].start_time == 0.0
            assert abs(chunks[0].end_time - 60.0) < 0.1

    def test_very_long_audio(self, tmp_path):
        """Test chunking of very long audio (4+ hours)."""
        # Create 3600s (1 hour) audio (using 1 hour instead of 4 to keep test faster)
        audio_path = create_test_audio(tmp_path, duration=3600, sample_rate=16000)

        mock_model = Mock()
        mock_get_speech_timestamps = Mock(return_value=[])

        with patch('torch.hub.load', return_value=(mock_model, [mock_get_speech_timestamps])):
            chunker = HybridChunker(max_chunk_length=600, overlap_length=10)
            chunks = chunker.chunk_audio(audio_path)

            # With 600s chunks and 10s overlap:
            # Chunk 1: 0-600, Chunk 2: 590-1190, Chunk 3: 1180-1780, etc.
            # Should create ~6 chunks for 1 hour
            assert len(chunks) >= 5
            assert len(chunks) <= 7

            # Verify all chunks are reasonable size
            for chunk in chunks:
                assert chunk.duration <= 600 + 1  # Allow small tolerance

    def test_audio_with_invalid_sample_rate(self, tmp_path):
        """Test error handling for non-16kHz audio."""
        # Create audio with 44.1kHz (non-standard for VAD)
        audio_path = create_test_audio(tmp_path, duration=10, sample_rate=44100)

        mock_model = Mock()
        mock_get_speech_timestamps = Mock(return_value=[])

        with patch('torch.hub.load', return_value=(mock_model, [mock_get_speech_timestamps])):
            chunker = HybridChunker()

            # The audio processor should load it, but VAD expects 16kHz
            # This test verifies the system handles different sample rates
            # (AudioProcessor.load_audio will load it as-is)
            chunks = chunker.chunk_audio(audio_path)

            # Should still create chunks, though VAD might not work optimally
            assert len(chunks) >= 1
            # Verify the sample rate is preserved
            assert chunks[0].sample_rate == 44100

    def test_audio_with_multiple_channels(self, tmp_path):
        """Test error handling for stereo audio."""
        import wave

        # Create stereo audio (2 channels)
        duration = 10
        sample_rate = 16000
        audio_data = np.zeros(duration * sample_rate * 2, dtype=np.int16)  # Stereo = 2 channels

        wav_path = tmp_path / "test_stereo.wav"
        with wave.open(str(wav_path), 'w') as wav_file:
            wav_file.setnchannels(2)  # Stereo
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())

        mock_model = Mock()
        mock_get_speech_timestamps = Mock(return_value=[])

        with patch('torch.hub.load', return_value=(mock_model, [mock_get_speech_timestamps])):
            chunker = HybridChunker()

            # The system should handle stereo by averaging to mono or taking one channel
            # soundfile.read will load it as stereo (shape: (samples, 2))
            chunks = chunker.chunk_audio(wav_path)

            # Should still create chunks
            assert len(chunks) >= 1


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.slow
@pytest.mark.skip(reason="Integration test - requires real audio fixtures (tests/fixtures/sample_speech.wav)")
def test_chunker_with_real_audio(tmp_path):
    """
    Integration test: Test chunker with real audio file containing speech and silence.

    This test is skipped by default as it requires:
    - Real audio file with speech/silence patterns (~30 seconds)
    - Path: tests/fixtures/sample_speech.wav

    When implemented, this test should:
    - Verify chunks split at detected silence boundaries
    - Verify overlap is preserved between chunks
    - Verify chunk timing is accurate
    """
    pass


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_audio(output_path: Path, duration: int, sample_rate: int = 16000):
    """
    Create a test WAV file.

    Args:
        output_path: Where to save the WAV file
        duration: Duration in seconds
        sample_rate: Sample rate in Hz

    Returns:
        Path to created WAV file
    """
    import wave

    # Create silent audio
    audio_data = np.zeros(duration * sample_rate, dtype=np.int16)

    wav_path = output_path / "test.wav"
    with wave.open(str(wav_path), 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)   # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())

    return wav_path


def create_test_audio_with_speech_pattern(
    output_path: Path,
    speech_segments: list,
    duration: int,
    sample_rate: int = 16000
):
    """
    Create test audio with specific speech/silence patterns.

    Args:
        output_path: Where to save the WAV file
        speech_segments: List of (start, end) tuples for speech
        duration: Total duration in seconds
        sample_rate: Sample rate in Hz

    Returns:
        Path to created WAV file

    Example:
        speech_segments = [(0, 10), (15, 25), (30, 40)]
        # Creates audio with speech at 0-10s, 15-25s, 30-40s
        # Silence everywhere else
    """
    import wave

    # Create silent audio
    audio_data = np.zeros(duration * sample_rate, dtype=np.int16)

    # Add "speech" (noise) to specified segments
    for start, end in speech_segments:
        start_sample = int(start * sample_rate)
        end_sample = int(end * sample_rate)
        # Use low-amplitude noise to simulate speech
        audio_data[start_sample:end_sample] = np.random.randint(
            -1000, 1000, size=end_sample - start_sample, dtype=np.int16
        )

    wav_path = output_path / "test_speech.wav"
    with wave.open(str(wav_path), 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())

    return wav_path
