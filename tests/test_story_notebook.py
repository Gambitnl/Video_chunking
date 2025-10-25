import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from src.story_notebook import StoryNotebookManager
from cli import cli as cli_root


def _write_session(tmp_path: Path, session_id: str, metadata: dict, segments: list) -> Path:
    session_dir = tmp_path / f"20250101_{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)
    json_path = session_dir / f"{session_id}_data.json"
    json_path.write_text(
        json.dumps({"metadata": metadata, "segments": segments}),
        encoding="utf-8",
    )
    return json_path


class StubGenerator:
    def __init__(self):
        self.narrator_calls = 0
        self.character_calls = []

    def generate_narrator_summary(self, **_: dict) -> str:
        self.narrator_calls += 1
        return "Narrator story"

    def generate_character_pov(self, *, character_name: str, **__: dict) -> str:
        self.character_calls.append(character_name)
        return f"{character_name} story"


def test_list_sessions_sorted_by_recent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first = _write_session(
        tmp_path,
        "session_a",
        {"session_id": "session_a"},
        [{"text": "hello", "classification": "IC"}],
    )
    second = _write_session(
        tmp_path,
        "session_b",
        {"session_id": "session_b"},
        [{"text": "world", "classification": "IC"}],
    )
    # Ensure second file appears newer
    second.touch()

    manager = StoryNotebookManager(output_dir=tmp_path)
    sessions = manager.list_sessions(limit=None)

    assert sessions == ["session_b", "session_a"]
    assert first.exists() and second.exists()


def test_load_session_and_build_info(tmp_path: Path) -> None:
    json_path = _write_session(
        tmp_path,
        "session_x",
        {
            "session_id": "session_x",
            "character_names": ["Alice", "Bob"],
            "statistics": {
                "ic_segments": 3,
                "ooc_segments": 1,
                "ic_percentage": 75.0,
                "total_duration_formatted": "01:00:00",
            },
        },
        [{"text": "line", "classification": "IC"}] * 4,
    )

    manager = StoryNotebookManager(output_dir=tmp_path)
    session = manager.load_session("session_x")

    assert session.session_id == "session_x"
    assert session.json_path == json_path
    assert len(session.segments) == 4
    assert session.character_names == ["Alice", "Bob"]

    info = manager.build_session_info(session)
    assert "- **Session ID**: `session_x`" in info
    assert "- **Segments**: 4 total (3 IC / 1 OOC)" in info
    assert "- **IC Share**: 75.0%" in info
    assert "- **Duration**: 01:00:00" in info
    assert "- **Characters**: Alice, Bob" in info


def test_save_and_generate_narratives(tmp_path: Path) -> None:
    json_path = _write_session(
        tmp_path,
        "session_story",
        {
            "session_id": "session_story",
            "character_names": ["Rogue"],
        },
        [{"text": "We explore.", "classification": "IC"}],
    )

    manager = StoryNotebookManager(output_dir=tmp_path)
    manager._generator = StubGenerator()
    session = manager.load_session("session_story")

    story_text = "A tale unfolds"
    saved = manager.save_narrative(
        session,
        perspective="Narrator",
        story=story_text,
    )

    assert saved.parent.name == "narratives"
    assert saved.read_text(encoding="utf-8") == story_text

    narrator_story, narrator_path = manager.generate_narrator(session, notebook_context="notes", temperature=0.2)
    assert narrator_story == "Narrator story"
    assert narrator_path.exists()

    character_story, character_path = manager.generate_character(session, "Rogue", notebook_context="notes", temperature=0.2)
    assert character_story == "Rogue story"
    assert character_path.exists()


def test_cli_generate_story_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    json_path = _write_session(
        tmp_path,
        "cli_session",
        {
            "session_id": "cli_session",
            "character_names": ["Cleric"],
        },
        [{"text": "Light shines.", "classification": "IC"}],
    )

    manager = StoryNotebookManager(output_dir=tmp_path)
    manager._generator = StubGenerator()

    def _factory(*_: object, **__: object) -> StoryNotebookManager:
        return manager

    monkeypatch.setattr("cli.StoryNotebookManager", _factory)

    runner = CliRunner()
    result = runner.invoke(cli_root, ["generate-story", "cli_session"])

    assert result.exit_code == 0, result.output
    narratives_dir = json_path.parent / "narratives"
    narrator_file = narratives_dir / "cli_session_narrator.md"
    cleric_file = narratives_dir / "cli_session_cleric.md"

    assert narrator_file.exists()
    assert cleric_file.exists()
    assert "Narratives for cli_session" in result.output
