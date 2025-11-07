"""Tests for helper functions powering the modern Characters tab."""
from typing import List

from src.ui import characters_tab_modern as ctab


def test_character_tab_snapshot_no_campaign():
    """No campaign selected should return an informative empty state."""
    snapshot = ctab.character_tab_snapshot(None)
    assert "No Campaign Selected" in snapshot["status"]
    assert snapshot["table"] == []
    assert snapshot["characters"] == []


def test_character_tab_snapshot_empty_campaign(monkeypatch):
    """Selected campaign with zero profiles yields warning state."""

    class DummyManager:
        def list_characters(self, campaign_id=None) -> List[str]:
            return []

        def get_profile(self, name: str):
            return None

    monkeypatch.setattr(ctab, "CharacterProfileManager", lambda: DummyManager())
    snapshot = ctab.character_tab_snapshot("camp-001")
    assert "No Profiles Found" in snapshot["status"]
    assert snapshot["table"] == []
    assert snapshot["characters"] == []


def test_character_tab_snapshot_with_profiles(monkeypatch):
    """Profiles present should produce table rows and success messaging."""

    class DummyProfile:
        def __init__(self, name: str, player: str):
            self.name = name
            self.player = player
            self.race = "Elf"
            self.class_name = "Wizard"
            self.level = 5
            self.total_sessions = 3

    class DummyManager:
        def __init__(self):
            self._profiles = {
                "Aria": DummyProfile("Aria", "Sam"),
                "Borin": DummyProfile("Borin", "Casey"),
            }

        def list_characters(self, campaign_id=None) -> List[str]:
            return sorted(self._profiles.keys())

        def get_profile(self, name: str):
            return self._profiles.get(name)

    monkeypatch.setattr(ctab, "CharacterProfileManager", lambda: DummyManager())
    snapshot = ctab.character_tab_snapshot("camp-002")

    assert "Profiles Loaded" in snapshot["status"]
    assert len(snapshot["table"]) == 2
    assert snapshot["characters"] == ["Aria", "Borin"]
