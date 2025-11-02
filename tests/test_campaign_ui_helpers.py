from pathlib import Path

from app import (
    Config,
    _campaign_overview_markdown,
    _character_profiles_markdown,
    _chat_status_markdown,
)


def test_campaign_overview_without_selection():
    result = _campaign_overview_markdown(None)
    assert "Select a campaign" in result


def test_campaign_overview_known_campaign():
    result = _campaign_overview_markdown("broken_seekers")
    assert "The Broken Seekers" in result
    assert "Campaign ID" in result


def test_chat_status_known_campaign_has_knowledge_file():
    result = _chat_status_markdown("broken_seekers")
    assert "Knowledge base" in result
    assert "broken_seekers" in result


def test_character_profiles_markdown_with_temp_profile():
    profiles_dir = Config.MODELS_DIR / "character_profiles"
    temp_profile_path = profiles_dir / "UI_Test_Profile.json"
    temp_profile_path.write_text(
        """
{
  "name": "UI Test Character",
  "player": "Tester",
  "race": "Elf",
  "class_name": "Wizard",
  "level": 5,
  "campaign_id": "ui_test_campaign",
  "last_updated": "2025-11-02T20:00:00",
  "notable_actions": [],
  "inventory": [],
  "relationships": [],
  "development_notes": [],
  "memorable_quotes": [],
  "sessions_appeared": [],
  "total_sessions": 0,
  "current_goals": [],
  "completed_goals": [],
  "dm_notes": "",
  "player_notes": ""
}
""".strip(),
        encoding="utf-8",
    )
    try:
        result = _character_profiles_markdown("ui_test_campaign")
        assert "UI Test Character" in result
        assert "Wizard" in result
    finally:
        if temp_profile_path.exists():
            temp_profile_path.unlink()
