import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import subprocess

import pytest

from src.config import Config
from src.snipper import AudioSnipper


class DummyAudioSegment:
    """Minimal stub that mimics the AudioSegment interface used by AudioSnipper."""

    def __getitem__(self, _slice):
        return self

    def export(self, path: str, format: str):
        Path(path).write_bytes(b"fake-audio-bytes")


@pytest.fixture(autouse=True)
def stub_audio_segment(monkeypatch):
    """
    Ensure tests never invoke the real pydub/ffmpeg stack.

    Disables streaming by default to prevent legacy tests from calling FFmpeg.
    Tests that explicitly test streaming mode override this with their own monkeypatch.
    """
    # Disable streaming by default for backward compatibility with legacy tests
    monkeypatch.setattr(
        "src.snipper.Config.USE_STREAMING_SNIPPET_EXPORT",
        False,
        raising=False
    )

    # Stub pydub for legacy mode
    dummy_segment = DummyAudioSegment()
    monkeypatch.setattr(
        "src.snipper.AudioSegment.from_file",
        lambda *args, **kwargs: dummy_segment,
    )
    yield

@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary directory for test outputs."""
    return tmp_path / "output"


@pytest.fixture
def dummy_audio_path(tmp_path):
    """Provide a placeholder audio path; file contents are irrelevant thanks to the stub."""
    return tmp_path / "session.wav"


@pytest.fixture
def sample_segments():
    """Provide sample transcription segments."""
    return [
        {"start_time": 1.0, "end_time": 3.0, "text": "Hello world", "speaker": "Player1"},
        {"start_time": 4.5, "end_time": 6.0, "text": "This is a test", "speaker": "DM"},
        {"start_time": 7.0, "end_time": 8.5, "text": "Another segment", "speaker": "Player1"},
    ]


def test_stale_clip_cleanup(monkeypatch, temp_output_dir, dummy_audio_path, sample_segments):
    """Verify that stale clips and manifest are removed before new export when cleanup is enabled."""
    monkeypatch.setattr("src.snipper.Config.CLEAN_STALE_CLIPS", True, raising=False)

    session_id = "test_session_cleanup"
    session_dir = temp_output_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # Create dummy stale files
    (session_dir / "stale_clip_1.wav").touch()
    (session_dir / "stale_clip_2.wav").touch()
    (session_dir / "manifest.json").touch()

    assert (session_dir / "stale_clip_1.wav").exists()
    assert (session_dir / "manifest.json").exists()

    snipper = AudioSnipper()
    snipper.export_segments(dummy_audio_path, sample_segments, temp_output_dir, session_id)

    assert not (session_dir / "stale_clip_1.wav").exists()
    assert not (session_dir / "stale_clip_2.wav").exists()
    assert (session_dir / "manifest.json").exists()
    assert len(list(session_dir.glob("segment_*.wav"))) == len(sample_segments)


def test_no_stale_clip_cleanup_when_disabled(monkeypatch, temp_output_dir, dummy_audio_path, sample_segments):
    """Verify that stale clips remain untouched when cleanup is disabled."""
    monkeypatch.setattr("src.snipper.Config.CLEAN_STALE_CLIPS", False, raising=False)

    session_id = "test_session_no_cleanup"
    session_dir = temp_output_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    stale_wav = session_dir / "stale_clip.wav"
    stale_wav.touch()

    snipper = AudioSnipper()
    snipper.export_segments(dummy_audio_path, sample_segments, temp_output_dir, session_id)

    assert stale_wav.exists()
    assert len(list(session_dir.glob("segment_*.wav"))) == len(sample_segments)


def test_export_segments_creates_files_and_manifest(monkeypatch, temp_output_dir, dummy_audio_path, sample_segments):
    """Test that segments are exported and the manifest is populated."""
    monkeypatch.setattr("src.snipper.Config.CLEAN_STALE_CLIPS", True, raising=False)

    session_id = "test_session_export"
    snipper = AudioSnipper()
    result = snipper.export_segments(dummy_audio_path, sample_segments, temp_output_dir, session_id)

    session_dir = temp_output_dir / session_id
    manifest_path = session_dir / "manifest.json"

    assert result["segments_dir"] == session_dir
    assert result["manifest"] == manifest_path

    wav_files = sorted(session_dir.glob("segment_*.wav"))
    assert [f.name for f in wav_files] == [
        "segment_0001_Player1.wav",
        "segment_0002_DM.wav",
        "segment_0003_Player1.wav",
    ]

    dummy_audio = DummyAudioSegment()
    monkeypatch.setattr("src.snipper.AudioSegment.from_file", lambda *args, **kwargs: dummy_audio)
    monkeypatch.setattr("src.snipper.Config.CLEAN_STALE_CLIPS", True, raising=False)


def test_export_with_no_segments(monkeypatch, temp_output_dir, dummy_audio_path):
    """When cleanup removes stale clips, write a placeholder manifest with neutral messaging."""
    monkeypatch.setattr("src.snipper.Config.CLEAN_STALE_CLIPS", True, raising=False)

    session_id = "test_empty_session"
    session_dir = temp_output_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    stale_file = session_dir / "old.wav"
    stale_file.write_bytes(b"legacy-bytes")
    keep_file = session_dir / "keep.txt"
    keep_file.write_text("legacy placeholder", encoding="utf-8")

    snipper = AudioSnipper()
    result = snipper.export_segments(dummy_audio_path, [], temp_output_dir, session_id)

    assert not stale_file.exists(), "Stale clips should be removed when cleanup is enabled"
    assert not keep_file.exists(), "Placeholder artifacts should be removed during cleanup"

    manifest_path = result["manifest"]
    assert manifest_path is not None
    session_dir = result["segments_dir"]
    assert session_dir == temp_output_dir / session_id
    assert session_dir.exists()

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["status"] == "no_snippets"
    assert data["total_clips"] == 0
    assert data["clips"] == []
    placeholder = data["placeholder"]
    assert placeholder["message"] == Config.SNIPPET_PLACEHOLDER_MESSAGE
    assert placeholder["reason"] == "no_segments"
    assert placeholder["removed_clips"] == 1


def test_export_with_no_segments_and_no_cleanup(monkeypatch, temp_output_dir, dummy_audio_path):
    """When cleanup is disabled, no placeholder manifest or directories should be created."""
    monkeypatch.setattr("src.snipper.Config.CLEAN_STALE_CLIPS", False, raising=False)

    snipper = AudioSnipper()
    result = snipper.export_segments(dummy_audio_path, [], temp_output_dir, "no_cleanup_session")

    assert result["manifest"] is None
    assert result["segments_dir"] is None
    assert not (temp_output_dir / "no_cleanup_session").exists()


def test_export_segments_skips_cleanup_when_disabled(tmp_path, monkeypatch):
    audio_path = tmp_path / "session.wav"
    audio_path.write_bytes(b"fake-audio")

    base_output = tmp_path / "segments"
    session_dir = base_output / "session-beta"
    session_dir.mkdir(parents=True)
    preserved = session_dir / "custom.wav"
    preserved.write_bytes(b"legacy")

    segments = [{
        "text": "Hallo opnieuw",
        "start_time": 0.0,
        "end_time": 1.0,
        "speaker": "SPEAKER_01"
    }]

    dummy_audio = DummyAudioSegment()
    monkeypatch.setattr("src.snipper.AudioSegment.from_file", lambda *args, **kwargs: dummy_audio)
    monkeypatch.setattr("src.snipper.Config.CLEAN_STALE_CLIPS", False, raising=False)

    snipper = AudioSnipper()
    snipper.export_segments(
        audio_path=audio_path,
        segments=segments,
        base_output_dir=base_output,
        session_id="session-beta",
        classifications=None
    )

    assert preserved.exists(), "Cleanup should be skipped when disabled"


# ============================================================================
# Streaming Export Tests (FFmpeg-based)
# ============================================================================

def test_ffmpeg_path_discovery_from_system_path(monkeypatch):
    """Test that FFmpeg is found in system PATH."""
    monkeypatch.setattr("src.snipper.Config.USE_STREAMING_SNIPPET_EXPORT", True, raising=False)

    with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
        snipper = AudioSnipper()
        assert snipper.use_streaming is True
        assert snipper.ffmpeg_path == "ffmpeg"


def test_ffmpeg_path_discovery_from_local_bundle(monkeypatch, tmp_path):
    """Test that FFmpeg is found in local bundle when not in PATH."""
    monkeypatch.setattr("src.snipper.Config.USE_STREAMING_SNIPPET_EXPORT", True, raising=False)
    monkeypatch.setattr("src.snipper.Config.PROJECT_ROOT", tmp_path, raising=False)

    # Create mock local FFmpeg
    local_ffmpeg_dir = tmp_path / "ffmpeg" / "bin"
    local_ffmpeg_dir.mkdir(parents=True)
    local_ffmpeg_exe = local_ffmpeg_dir / "ffmpeg.exe"
    local_ffmpeg_exe.touch()

    with patch('shutil.which', return_value=None):
        snipper = AudioSnipper()
        assert snipper.use_streaming is True
        assert str(local_ffmpeg_exe) in snipper.ffmpeg_path


def test_streaming_segment_extraction_success(monkeypatch, tmp_path):
    """Test successful FFmpeg segment extraction."""
    monkeypatch.setattr("src.snipper.Config.USE_STREAMING_SNIPPET_EXPORT", True, raising=False)

    audio_path = tmp_path / "session.wav"
    audio_path.write_bytes(b"fake-audio")
    output_path = tmp_path / "segment.wav"

    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
        snipper = AudioSnipper()

        with patch('subprocess.run', return_value=mock_result) as mock_run:
            snipper._extract_segment_with_ffmpeg(
                audio_path=audio_path,
                start_time=1.5,
                end_time=3.0,
                output_path=output_path
            )

            # Verify FFmpeg command
            call_args = mock_run.call_args
            command = call_args[0][0]
            assert command[0] == "ffmpeg"
            assert "-ss" in command
            assert "1.500" in command  # Start time
            assert "-t" in command
            assert "1.500" in command  # Duration (3.0 - 1.5)
            assert "-i" in command
            assert str(audio_path) in command
            assert str(output_path) in command


def test_streaming_segment_extraction_ffmpeg_error(monkeypatch, tmp_path):
    """Test FFmpeg extraction error handling."""
    monkeypatch.setattr("src.snipper.Config.USE_STREAMING_SNIPPET_EXPORT", True, raising=False)

    audio_path = tmp_path / "session.wav"
    output_path = tmp_path / "segment.wav"

    with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
        snipper = AudioSnipper()

        mock_error = subprocess.CalledProcessError(
            returncode=1,
            cmd=['ffmpeg'],
            stderr="FFmpeg error: invalid input"
        )

        with patch('subprocess.run', side_effect=mock_error):
            with pytest.raises(RuntimeError, match="FFmpeg extraction failed"):
                snipper._extract_segment_with_ffmpeg(
                    audio_path=audio_path,
                    start_time=0.0,
                    end_time=1.0,
                    output_path=output_path
                )


def test_streaming_segment_extraction_timeout(monkeypatch, tmp_path):
    """Test FFmpeg extraction timeout handling."""
    monkeypatch.setattr("src.snipper.Config.USE_STREAMING_SNIPPET_EXPORT", True, raising=False)

    audio_path = tmp_path / "session.wav"
    output_path = tmp_path / "segment.wav"

    with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
        snipper = AudioSnipper()

        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('ffmpeg', 30)):
            with pytest.raises(RuntimeError, match="FFmpeg extraction timed out"):
                snipper._extract_segment_with_ffmpeg(
                    audio_path=audio_path,
                    start_time=0.0,
                    end_time=1.0,
                    output_path=output_path
                )


def test_streaming_mode_enabled_uses_ffmpeg(monkeypatch, temp_output_dir, sample_segments):
    """Test that streaming mode uses FFmpeg, not pydub."""
    monkeypatch.setattr("src.snipper.Config.USE_STREAMING_SNIPPET_EXPORT", True, raising=False)
    monkeypatch.setattr("src.snipper.Config.CLEAN_STALE_CLIPS", True, raising=False)

    audio_path = temp_output_dir / "session.wav"
    audio_path.write_bytes(b"fake-audio")

    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
        snipper = AudioSnipper()

        with patch('subprocess.run', return_value=mock_result) as mock_run:
            snipper.export_segments(
                audio_path=audio_path,
                segments=sample_segments,
                base_output_dir=temp_output_dir,
                session_id="streaming_test"
            )

            # Verify FFmpeg was called for each segment
            assert mock_run.call_count == len(sample_segments)

            # Verify manifest was created
            manifest_path = temp_output_dir / "streaming_test" / "manifest.json"
            assert manifest_path.exists()

            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert manifest_data["status"] == "complete"
            assert manifest_data["total_clips"] == len(sample_segments)


def test_legacy_mode_uses_pydub(monkeypatch, temp_output_dir, sample_segments):
    """Test that legacy mode (streaming disabled) uses pydub."""
    monkeypatch.setattr("src.snipper.Config.USE_STREAMING_SNIPPET_EXPORT", False, raising=False)
    monkeypatch.setattr("src.snipper.Config.CLEAN_STALE_CLIPS", True, raising=False)

    audio_path = temp_output_dir / "session.wav"
    audio_path.write_bytes(b"fake-audio")

    # Stub pydub
    dummy_audio = DummyAudioSegment()
    monkeypatch.setattr("src.snipper.AudioSegment.from_file", lambda *args, **kwargs: dummy_audio)

    snipper = AudioSnipper()
    assert snipper.use_streaming is False

    # Should not raise (pydub path works)
    result = snipper.export_segments(
        audio_path=audio_path,
        segments=sample_segments,
        base_output_dir=temp_output_dir,
        session_id="legacy_test"
    )

    # Verify manifest was created
    manifest_path = result["manifest"]
    assert manifest_path.exists()

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["status"] == "complete"
    assert manifest_data["total_clips"] == len(sample_segments)


def test_minimum_segment_duration_enforced(monkeypatch, tmp_path):
    """Test that minimum segment duration (0.01s) is enforced."""
    monkeypatch.setattr("src.snipper.Config.USE_STREAMING_SNIPPET_EXPORT", True, raising=False)

    audio_path = tmp_path / "session.wav"
    output_path = tmp_path / "segment.wav"

    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
        snipper = AudioSnipper()

        with patch('subprocess.run', return_value=mock_result) as mock_run:
            # Zero-duration segment should be clamped to 0.01s
            snipper._extract_segment_with_ffmpeg(
                audio_path=audio_path,
                start_time=5.0,
                end_time=5.0,  # Same as start
                output_path=output_path
            )

            # Verify duration was set to minimum 0.01s
            call_args = mock_run.call_args
            command = call_args[0][0]
            duration_idx = command.index("-t") + 1
            duration = float(command[duration_idx])
            assert duration == 0.01
