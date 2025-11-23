"""Tests for CharacterProfileExtractor end-to-end workflow."""
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from src.character_profile import (
    CharacterProfileManager,
    ProfileUpdate,
    ProfileUpdateBatch,
)
from src.character_profile_extractor import CharacterProfileExtractor, ExtractedCharacterData
from src.party_config import Character, PartyConfigManager
from src import config as config_module


@pytest.fixture(autouse=True)
def stub_profile_extractor(monkeypatch):
    """Avoid real Ollama connections by providing a lightweight extractor stub."""

    class StubExtractor:
        def __init__(self, *args, **kwargs):
            pass

        def extract_profile_updates(self, **kwargs):
            return ProfileUpdateBatch(
                session_id=kwargs.get("session_id", "test_session"),
                campaign_id=kwargs.get("campaign_id", "test_campaign"),
                generated_at=kwargs.get("generated_at", "1970-01-01T00:00:00Z"),
                source={},
                updates=[],
            )

    monkeypatch.setattr("src.character_profile_extractor.ProfileExtractor", StubExtractor)


class TestCharacterProfileExtractor:
    """Test the high-level profile extraction workflow."""

    def test_extractor_initialization(self):
        extractor = CharacterProfileExtractor()
        assert extractor is not None
        assert extractor.extractor is not None

    def test_parse_transcript_with_timestamps(self, tmp_path):
        extractor = CharacterProfileExtractor()

        transcript_text = """[00:12:34] Thorin: I charge into battle!
[00:15:45] Elara: I cast healing word on Thorin.
[01:23:00] DM: You rolled a natural 20!"""

        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text(transcript_text, encoding="utf-8")

        segments = extractor._parse_plaintext_transcript(transcript_path)

        assert len(segments) == 3
        assert segments[0]["speaker"] == "Thorin"
        assert segments[0]["text"] == "I charge into battle!"
        assert segments[0]["start"] == 12 * 60 + 34

    def test_parse_transcript_without_timestamps(self, tmp_path):
        extractor = CharacterProfileExtractor()

        transcript_text = """Thorin charges forward.
Elara casts a spell.
The goblin attacks!"""

        transcript_path = tmp_path / "transcript_no_ts.txt"
        transcript_path.write_text(transcript_text, encoding="utf-8")

        segments = extractor._parse_plaintext_transcript(transcript_path)

        assert len(segments) == 3
        assert all(seg["start"] == float(i) for i, seg in enumerate(segments))
        assert all(seg["speaker"] == "Unknown" for seg in segments)

    def test_resolve_character_name_handles_alias(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module.Config, "MODELS_DIR", tmp_path)
        extractor = CharacterProfileExtractor()

        character_lookup = {
            "Furnax": Character(name="Furnax", player="Companion", race="", class_name=""),
            "Sha'ek Mindfa'ek": Character(name="Sha'ek Mindfa'ek", player="Player", race="", class_name="", aliases=["Sha'ek"]),
        }

        resolved = extractor._resolve_character_name(
            "Sha'ek",
            character_lookup,
        )
        assert resolved == "Sha'ek Mindfa'ek"

    def test_format_action(self):
        extractor = CharacterProfileExtractor()
        update = ProfileUpdate(
            character="Thorin",
            category="notable_actions",
            content="Rolled natural 20 on intimidation",
            timestamp="01:23:45",
            context="Confronting the goblin chief",
        )

        formatted = extractor._format_action(update)
        assert "Rolled natural 20" in formatted
        assert "01:23:45" in formatted
        assert "goblin chief" in formatted

    def test_format_quote(self):
        extractor = CharacterProfileExtractor()
        update = ProfileUpdate(
            character="Elara",
            category="memorable_quotes",
            content="I will not abandon my friends!",
            quote="I will not abandon my friends!",
            timestamp="02:15:30",
        )

        formatted = extractor._format_quote(update)
        assert '"' in formatted
        assert "abandon" in formatted
        assert "02:15:30" in formatted

    def test_has_updates_with_data(self):
        extractor = CharacterProfileExtractor()
        extracted = ExtractedCharacterData(
            character_name="Thorin",
            notable_actions=["Did something"],
        )

        assert extractor._has_updates(extracted) is True

    def test_has_updates_empty(self):
        extractor = CharacterProfileExtractor()
        extracted = ExtractedCharacterData(character_name="Thorin")

        assert extractor._has_updates(extracted) is False

    @pytest.mark.slow
    def test_batch_extract_requires_party_config(self):
        extractor = CharacterProfileExtractor()
        profile_mgr = CharacterProfileManager()
        party_mgr = PartyConfigManager()

        with NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("[00:01:00] Thorin: I attack!\n")
            transcript_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="not found"):
                extractor.batch_extract_and_update(
                    transcript_path=transcript_path,
                    party_id="nonexistent_party",
                    session_id="test_session",
                    profile_manager=profile_mgr,
                    party_manager=party_mgr,
                )
        finally:
            transcript_path.unlink()

    def test_extracted_character_data_initialization(self):
        data = ExtractedCharacterData(character_name="Thorin")

        assert data.character_name == "Thorin"
        assert data.notable_actions == []
        assert data.items_acquired == []
        assert data.memorable_quotes == []
        assert data.character_development == []

    def test_batch_extract_updates_profiles(self, tmp_path, monkeypatch):
        party_config_path = tmp_path / "parties.json"
        party_config_path.write_text(
            json.dumps(
                {
                    "party_alpha": {
                        "party_name": "Alpha Team",
                        "dm_name": "GM",
                        "campaign": "Shadowfell Chronicles",
                        "notes": "Test party",
                        "characters": [
                            {
                                "name": "Thorin",
                                "player": "Alice",
                                "race": "Dwarf",
                                "class_name": "Fighter",
                                "aliases": ["The Hammer"],
                            }
                        ],
                    }
                }
            ),
            encoding="utf-8",
        )

        # Ensure character profiles write into the temporary directory
        monkeypatch.setattr(config_module.Config, "MODELS_DIR", tmp_path)

        party_mgr = PartyConfigManager(config_file=party_config_path)
        profiles_dir = tmp_path / "profiles"
        profile_mgr = CharacterProfileManager(profiles_dir=profiles_dir)

        update = ProfileUpdate(
            character="thorin",
            category="notable_actions",
            content="Slays the dragon with a single strike",
            timestamp="00:10:00",
            context="The climactic battle in the forge",
        )
        batch = ProfileUpdateBatch(
            session_id="session_123",
            campaign_id="party_alpha",
            generated_at="2025-10-31T12:00:00Z",
            source={"origin": "unit-test"},
            updates=[update],
        )

        class StubExtractor:
            def extract_profile_updates(self, **kwargs):
                return batch

        extractor = CharacterProfileExtractor(profile_extractor=StubExtractor())

        transcript_path = tmp_path / "session.txt"
        transcript_path.write_text("[00:10:00] Thorin: For the Seekers!\n", encoding="utf-8")

        results = extractor.batch_extract_and_update(
            transcript_path=transcript_path,
            party_id="party_alpha",
            session_id="session_123",
            profile_manager=profile_mgr,
            party_manager=party_mgr,
            campaign_id="campaign_xyz",
        )

        assert "Thorin" in results
        extracted = results["Thorin"]
        assert extracted.notable_actions

        profile = profile_mgr.get_profile("Thorin")
        assert profile is not None
        assert any("dragon" in action.description for action in profile.notable_actions)
        assert "session_123" in profile.sessions_appeared
        assert profile.total_sessions == len(profile.sessions_appeared)
        assert profile.campaign_id == "campaign_xyz"
