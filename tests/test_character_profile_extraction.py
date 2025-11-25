"""Tests for the CharacterProfileExtractor class."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import time


from src.character_profile_extractor import CharacterProfileExtractor
from src.party_config import PartyConfigManager, Character
from src.character_profile import CharacterProfileManager, ProfileUpdate, ProfileUpdateBatch


def create_long_transcript(tmp_path: Path, num_lines: int) -> Path:
    """Creates a long transcript file for testing."""
    transcript_path = tmp_path / "long_transcript.txt"
    with open(transcript_path, "w", encoding='utf-8') as f:
        for i in range(num_lines):
            speaker = f"Character{(i % 4) + 1}"
            f.write(f"[00:00:{i:02d}] {speaker}: This is line {i + 1} of the transcript.\n")
    return transcript_path


class TestCharacterProfileExtractor:
    """Test suite for the CharacterProfileExtractor."""

    @pytest.mark.slow
    def test_batch_extract_and_update_with_long_transcript(self, tmp_path):
        """
        Tests the performance and correctness of batch_extract_and_update
        with a transcript of over 10,000 lines.
        """
        # 1. Setup
        num_lines = 10001
        transcript_path = create_long_transcript(tmp_path, num_lines)

        # Mock dependencies
        mock_party_manager = MagicMock(spec=PartyConfigManager)
        mock_profile_manager = MagicMock(spec=CharacterProfileManager)
        mock_profile_extractor = MagicMock()

        # Setup mock party configuration
        characters = [
            Character(name="Character1", player="Player1", race="Human", class_name="Fighter"),
            Character(name="Character2", player="Player2", race="Elf", class_name="Ranger"),
            Character(name="Character3", player="Player3", race="Dwarf", class_name="Cleric"),
            Character(name="Character4", player="Player4", race="Halfling", class_name="Rogue"),
        ]
        mock_party = MagicMock()
        mock_party.characters = characters
        mock_party.campaign = "Test Campaign"
        mock_party.notes = "Some notes about the campaign."
        mock_party_manager.get_party.return_value = mock_party

        # Setup mock LLM extractor response
        mock_updates = [
            ProfileUpdate(character="Character1", category="notable_actions", content="Did something cool.")
        ]
        mock_batch = ProfileUpdateBatch(session_id="test_session", updates=mock_updates)
        mock_profile_extractor.extract_profile_updates.return_value = mock_batch

        # 2. Execute
        extractor = CharacterProfileExtractor(profile_extractor=mock_profile_extractor)

        start_time = time.time()
        results = extractor.batch_extract_and_update(
            transcript_path=transcript_path,
            party_id="test_party",
            session_id="test_session",
            profile_manager=mock_profile_manager,
            party_manager=mock_party_manager,
            campaign_id="test_campaign",
        )
        end_time = time.time()
        duration = end_time - start_time

        # 3. Assert
        # Check that the underlying extractor was called
        mock_profile_extractor.extract_profile_updates.assert_called_once()

        # Check that the number of segments passed to the extractor is correct
        args, kwargs = mock_profile_extractor.extract_profile_updates.call_args
        assert len(kwargs['transcript_segments']) == num_lines

        # Check that profiles were merged
        mock_profile_manager.merge_updates.assert_called()
        assert mock_profile_manager.merge_updates.call_count > 0

        # Check the results
        assert "Character1" in results
        assert len(results["Character1"].notable_actions) == 1
        assert results["Character1"].notable_actions[0] == "Did something cool."

        # Check performance (adjust threshold as needed)
        assert duration < 5.0, f"Processing long transcript took {duration:.2f}s, exceeding the 5s threshold."
