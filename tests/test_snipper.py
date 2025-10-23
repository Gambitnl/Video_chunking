import json
from pathlib import Path

import pytest

from src.snipper import AudioSnipper


class DummyAudioSegment:
    """Minimal stub that mimics the AudioSegment interface used by AudioSnipper."""

    def __getitem__(self, _slice):
        return self

    def export(self, path: str, format: str):
        Path(path).write_bytes(b"fake-audio-bytes")


@pytest.fixture(autouse=True)
def stub_audio_segment(monkeypatch):
    """Ensure tests never invoke the real pydub/ffmpeg stack."""
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

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest_data) == 3
    assert manifest_data[0]["speaker"] == "Player1"
    assert manifest_data[1]["speaker"] == "DM"


def test_export_with_no_segments(temp_output_dir, dummy_audio_path):
    """Ensure empty segment lists are handled gracefully."""
    snipper = AudioSnipper()
    result = snipper.export_segments(dummy_audio_path, [], temp_output_dir, "test_empty_session")

    assert result["segments_dir"] is None
    assert result["manifest"] is None

    session_dir = temp_output_dir / "test_empty_session"
    assert not session_dir.exists()


def test_filename_sanitization(monkeypatch, temp_output_dir, dummy_audio_path):
    """Speaker names should be sanitized to create safe filenames."""
    monkeypatch.setattr("src.snipper.Config.CLEAN_STALE_CLIPS", True, raising=False)

    segments = [
        {"start_time": 1.0, "end_time": 2.0, "speaker": "Player 1 (Test)"},
        {"start_time": 3.0, "end_time": 4.0, "speaker": "D&D_Master"},
    ]

    snipper = AudioSnipper()
    snipper.export_segments(dummy_audio_path, segments, temp_output_dir, "test_sanitize")

    wav_files = sorted((temp_output_dir / "test_sanitize").glob("segment_*.wav"))
    assert [f.name for f in wav_files] == [
        "segment_0001_Player_1_Test.wav",
        "segment_0002_D_D_Master.wav",
    ]
