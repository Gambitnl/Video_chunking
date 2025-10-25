"""
Test suite for streaming snippet export in src/snipper.py
"""
import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.snipper import AudioSnipper

@pytest.fixture
def audio_snipper():
    return AudioSnipper()

def test_initialize_manifest(audio_snipper, tmp_path):
    session_dir = tmp_path / "session1"
    manifest_path = audio_snipper.initialize_manifest(session_dir)

    assert manifest_path.exists()
    with open(manifest_path, "r") as f:
        manifest_data = json.load(f)

    assert manifest_data["status"] == "in_progress"
    assert manifest_data["total_clips"] == 0
    assert len(manifest_data["clips"]) == 0

def test_export_incremental(audio_snipper, tmp_path):
    session_dir = tmp_path / "session1"
    audio_path = tmp_path / "test.wav"
    audio_path.touch()

    manifest_path = audio_snipper.initialize_manifest(session_dir)

    segment = {
        'start_time': 0.0,
        'end_time': 1.0,
        'speaker': 'SPEAKER_00',
        'text': 'Hello world'
    }

    with patch('pydub.AudioSegment.from_file') as mock_from_file:
        mock_audio_segment = MagicMock()
        mock_audio_segment.__getitem__.return_value = MagicMock()
        mock_from_file.return_value = mock_audio_segment

        audio_snipper.export_incremental(audio_path, segment, 1, session_dir, manifest_path)

        mock_from_file.assert_called_once_with(str(audio_path))
        mock_audio_segment.__getitem__.assert_called_once_with(slice(0, 1000, None))
        mock_audio_segment.__getitem__.return_value.export.assert_called_once()

    with open(manifest_path, "r") as f:
        manifest_data = json.load(f)

    assert manifest_data["total_clips"] == 1
    assert len(manifest_data["clips"]) == 1
    clip = manifest_data["clips"][0]
    assert clip["id"] == 1
    assert clip["status"] == "ready"

def test_export_segments_completes_manifest(audio_snipper, tmp_path):
    session_dir = tmp_path / "session1"
    audio_path = tmp_path / "test.wav"
    audio_path.touch()

    segments = [
        {
            'start_time': 0.0,
            'end_time': 1.0,
            'speaker': 'SPEAKER_00',
            'text': 'Hello world'
        }
    ]

    with patch('pydub.AudioSegment.from_file') as mock_from_file:
        mock_audio_segment = MagicMock()
        mock_from_file.return_value = mock_audio_segment

        audio_snipper.export_segments(audio_path, segments, session_dir, "session1")

    manifest_path = session_dir / "session1" / "manifest.json"
    with open(manifest_path, "r") as f:
        manifest_data = json.load(f)

    assert manifest_data["status"] == "complete"
