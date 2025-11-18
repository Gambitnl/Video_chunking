from pathlib import Path

import pytest
from click.testing import CliRunner

import cli as cli_module


@pytest.fixture(autouse=True)
def _disable_audit(monkeypatch):
    monkeypatch.setattr(cli_module, "audit_enabled", lambda: False)


def test_cli_process_invokes_pipeline(monkeypatch, tmp_path):
    called = {}

    class DummyProcessor:
        def __init__(self, session_id, **kwargs):
            called["session_id"] = session_id
            called["kwargs"] = kwargs
            self.session_id = session_id
            self._output_dir = kwargs.get("output_dir", tmp_path / "output")

        def process(self, input_file, output_dir, skip_diarization, skip_classification, skip_snippets):
            called["process_called"] = True
            called["input_file"] = Path(input_file)
            called["process_kwargs"] = {
                "output_dir": output_dir,
                "skip_diarization": skip_diarization,
                "skip_classification": skip_classification,
                "skip_snippets": skip_snippets,
            }
            return {"session_id": self.session_id, "statistics": {}}

    monkeypatch.setattr(cli_module, "DDSessionProcessor", DummyProcessor)

    audio_file = tmp_path / "session.wav"
    audio_file.write_bytes(b"dummy")

    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli,
        [
            "process",
            str(audio_file),
            "--session-id",
            "test_session",
            "--characters",
            "Hero",
            "--players",
            "Player1",
            "--skip-classification",
        ],
    )

    assert result.exit_code == 0, result.output
    assert called["process_called"] is True
    assert called["session_id"] == "test_session"
    assert called["input_file"] == audio_file
    assert called["kwargs"]["character_names"] == ["Hero"]
    assert called["kwargs"]["player_names"] == ["Player1"]
    assert called["process_kwargs"]["skip_classification"] is True
