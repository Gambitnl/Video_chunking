import json
from pathlib import Path
from types import SimpleNamespace

from src.snipper import AudioSnipper


class DummyAudioSegment:
    """Minimal stub to emulate pydub AudioSegment behaviour for tests."""

    def __getitem__(self, _slice):
        return self

    def export(self, path: str, format: str):
        Path(path).write_bytes(b"audio-bytes")


def test_export_segments_cleans_directory_and_builds_manifest(tmp_path, monkeypatch):
    audio_path = tmp_path / "session.wav"
    audio_path.write_bytes(b"fake-audio")

    base_output = tmp_path / "segments"
    stale_dir = base_output / "session-alpha"
    stale_dir.mkdir(parents=True)
    (stale_dir / "old.wav").write_bytes(b"stale")

    segments = [
        {
            "text": "Hallo wereld",
            "start_time": 0.0,
            "end_time": 1.25,
            "speaker": "SPEAKER_00"
        }
    ]
    classifications = [
        SimpleNamespace(
            classification="IC",
            confidence=0.9,
            reasoning="Unit test",
            character="DM"
        )
    ]

    dummy_audio = DummyAudioSegment()
    monkeypatch.setattr("src.snipper.AudioSegment.from_file", lambda *args, **kwargs: dummy_audio)

    snipper = AudioSnipper()
    result = snipper.export_segments(
        audio_path=audio_path,
        segments=segments,
        base_output_dir=base_output,
        session_id="session-alpha",
        classifications=classifications
    )

    session_dir = result["segments_dir"]
    assert session_dir is not None
    assert session_dir.exists()
    assert not (session_dir / "old.wav").exists(), "Stale files should be removed"

    manifest_path = result["manifest"]
    assert manifest_path is not None
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data[0]["text"] == "Hallo wereld"
    assert data[0]["classification"]["label"] == "IC"
    assert data[0]["classification"]["confidence"] == 0.9
    assert data[0]["classification"]["reasoning"] == "Unit test"
    assert data[0]["classification"]["character"] == "DM"
