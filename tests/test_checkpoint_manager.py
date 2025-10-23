from pathlib import Path
from time import sleep

from src.checkpoint import CheckpointManager


def test_checkpoint_save_and_load(tmp_path):
    manager = CheckpointManager("session-1", tmp_path)

    manager.save(
        "audio_converted",
        {"wav_path": "/tmp/audio.wav"},
        completed_stages=["audio_converted"],
        metadata={"input": "file.m4a"},
    )

    record = manager.load("audio_converted")
    assert record is not None
    assert record.session_id == "session-1"
    assert record.stage == "audio_converted"
    assert record.data["wav_path"] == "/tmp/audio.wav"
    assert record.completed_stages == ["audio_converted"]
    assert record.metadata == {"input": "file.m4a"}


def test_checkpoint_latest_and_clear(tmp_path):
    manager = CheckpointManager("session-2", tmp_path)

    manager.save("stage_one", {"value": 1})
    sleep(0.01)  # ensure different modification times
    manager.save("stage_two", {"value": 2})

    latest = manager.latest()
    assert latest is not None
    stage, record = latest
    assert stage == "stage_two"
    assert record.data["value"] == 2

    assert manager.has_checkpoint("stage_two")
    assert set(manager.list_stages()) == {"stage_one", "stage_two"}

    manager.clear()
    assert manager.list_stages() == []
