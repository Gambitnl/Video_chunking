"""Tests for CharacterProfileExtractor with long transcripts."""
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
import pytest
from unittest.mock import MagicMock

from src.character_profile import (
    CharacterProfileManager,
    ProfileUpdate,
    ProfileUpdateBatch,
)
from src.character_profile_extractor import CharacterProfileExtractor, ExtractedCharacterData
from src.party_config import Character, PartyConfigManager
from src import config as config_module

# Mock the ProfileExtractor to avoid actual LLM calls
@pytest.fixture
def mock_profile_extractor():
    extractor = MagicMock()
    # Mock extract_profile_updates to return an empty batch or a batch with some dummy updates
    extractor.extract_profile_updates.return_value = ProfileUpdateBatch(
        session_id="test_session",
        campaign_id="test_campaign",
        generated_at="2025-01-01T00:00:00Z",
        source={},
        updates=[]
    )
    return extractor

class TestCharacterProfileExtractorLong:
    """Test the high-level profile extraction workflow with long transcripts."""

    def test_extract_profiles_with_very_long_transcript(self, tmp_path, mock_profile_extractor, monkeypatch):
        # Setup configuration
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

        monkeypatch.setattr(config_module.Config, "MODELS_DIR", tmp_path)
        party_mgr = PartyConfigManager(config_file=party_config_path)
        profiles_dir = tmp_path / "profiles"
        profile_mgr = CharacterProfileManager(profiles_dir=profiles_dir)

        # Initialize Extractor with the mock
        extractor = CharacterProfileExtractor(profile_extractor=mock_profile_extractor)

        # Create a large transcript file (e.g., 10,000 lines)
        num_lines = 10000
        transcript_path = tmp_path / "long_session.txt"
        with open(transcript_path, "w", encoding="utf-8") as f:
            for i in range(num_lines):
                f.write(f"[00:{i%60:02d}:00] Thorin: I attack the goblin {i}!\n")

        # Run extraction
        results = extractor.batch_extract_and_update(
            transcript_path=transcript_path,
            party_id="party_alpha",
            session_id="session_long",
            profile_manager=profile_mgr,
            party_manager=party_mgr,
            campaign_id="campaign_xyz",
        )

        # Verify that the mock was called
        # The extractor should process all segments.
        # Check if extract_profile_updates was called.
        assert mock_profile_extractor.extract_profile_updates.called

        # Verify that we processed the segments
        # Since we mocked the return to be empty, we expect no updates in results,
        # but the key thing is that it didn't crash.
        assert isinstance(results, dict)
