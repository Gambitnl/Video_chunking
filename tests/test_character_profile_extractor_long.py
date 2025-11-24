"""
Regression test for BUG-20251102-49: Character Profile Extraction with very long transcripts.
"""
import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from src.character_profile_extractor import CharacterProfileExtractor
from src.character_profile import CharacterProfileManager, ProfileUpdateBatch
from src.party_config import PartyConfigManager
from src import config as config_module

class TestCharacterProfileExtractorLong(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

        # Mock ProfileExtractor
        self.stub_patcher = patch("src.character_profile_extractor.ProfileExtractor")
        self.mock_extractor_cls = self.stub_patcher.start()
        self.mock_extractor_instance = MagicMock()
        self.mock_extractor_cls.return_value = self.mock_extractor_instance

        # Return empty batch by default to avoid processing logic errors
        self.mock_extractor_instance.extract_profile_updates.return_value = ProfileUpdateBatch(
            session_id="long_session",
            campaign_id="test_campaign",
            generated_at="2025-01-01T00:00:00Z",
            source={},
            updates=[],
        )

    def tearDown(self):
        self.stub_patcher.stop()
        self.temp_dir.cleanup()

    def test_process_very_long_transcript(self):
        """
        Test processing a transcript with thousands of lines to ensure no OOM or timeout crashes.
        BUG-20251102-49
        """
        extractor = CharacterProfileExtractor()

        # Generate a large transcript (e.g., 10,000 lines ~ 1MB+)
        lines = []
        for i in range(10000):
            speaker = "Thorin" if i % 2 == 0 else "DM"
            lines.append(f"[{i//60:02d}:{i%60:02d}:00] {speaker}: This is line {i} of the very long transcript to test performance.")

        transcript_text = "\n".join(lines)
        transcript_path = self.tmp_path / "long_transcript.txt"
        transcript_path.write_text(transcript_text, encoding="utf-8")

        # Setup managers
        party_config_path = self.tmp_path / "parties.json"
        party_config_path.write_text(json.dumps({"default": {"party_name": "Default", "characters": [{"name": "Thorin"}]}}), encoding="utf-8")

        with patch.object(config_module.Config, "MODELS_DIR", self.tmp_path):
            party_mgr = PartyConfigManager(config_file=party_config_path)
            profile_mgr = CharacterProfileManager(profiles_dir=self.tmp_path / "profiles")

            # This should complete reasonably fast (e.g. < 5 seconds for parsing)
            # The actual LLM call is mocked, so we are testing the parsing and batching logic overhead.
            import time
            start_time = time.time()

            extractor.batch_extract_and_update(
                transcript_path=transcript_path,
                party_id="default",
                session_id="long_session",
                profile_manager=profile_mgr,
                party_manager=party_mgr
            )

            end_time = time.time()
            duration = end_time - start_time

            print(f"Processed {len(lines)} lines in {duration:.4f}s")
            self.assertLess(duration, 30.0, "Processing took too long")
