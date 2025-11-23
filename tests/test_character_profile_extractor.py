"""Tests for CharacterProfileExtractor end-to-end workflow."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from src.character_profile import (
    CharacterProfileManager,
    ProfileUpdate,
    ProfileUpdateBatch,
)
from src.character_profile_extractor import CharacterProfileExtractor, ExtractedCharacterData
from src.party_config import Character, PartyConfigManager
from src import config as config_module


class TestCharacterProfileExtractor(unittest.TestCase):
    """Test the high-level profile extraction workflow."""

    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

        # Stub the ProfileExtractor to avoid external connections
        self.stub_patcher = patch("src.character_profile_extractor.ProfileExtractor")
        self.mock_extractor_cls = self.stub_patcher.start()

        self.mock_extractor_instance = MagicMock()
        self.mock_extractor_cls.return_value = self.mock_extractor_instance

        # Default mock return value
        self.mock_extractor_instance.extract_profile_updates.return_value = ProfileUpdateBatch(
            session_id="test_session",
            campaign_id="test_campaign",
            generated_at="1970-01-01T00:00:00Z",
            source={},
            updates=[],
        )

    def tearDown(self):
        self.stub_patcher.stop()
        self.temp_dir.cleanup()

    def test_extractor_initialization(self):
        extractor = CharacterProfileExtractor()
        self.assertIsNotNone(extractor)
        self.assertIsNotNone(extractor.extractor)

    def test_parse_transcript_with_timestamps(self):
        extractor = CharacterProfileExtractor()

        transcript_text = """[00:12:34] Thorin: I charge into battle!
[00:15:45] Elara: I cast healing word on Thorin.
[01:23:00] DM: You rolled a natural 20!"""

        transcript_path = self.tmp_path / "transcript.txt"
        transcript_path.write_text(transcript_text, encoding="utf-8")

        segments = extractor._parse_plaintext_transcript(transcript_path)

        self.assertEqual(len(segments), 3)
        self.assertEqual(segments[0]["speaker"], "Thorin")
        self.assertEqual(segments[0]["text"], "I charge into battle!")
        self.assertEqual(segments[0]["start"], 12 * 60 + 34)

    def test_parse_transcript_without_timestamps(self):
        extractor = CharacterProfileExtractor()

        transcript_text = """Thorin charges forward.
Elara casts a spell.
The goblin attacks!"""

        transcript_path = self.tmp_path / "transcript_no_ts.txt"
        transcript_path.write_text(transcript_text, encoding="utf-8")

        segments = extractor._parse_plaintext_transcript(transcript_path)

        self.assertEqual(len(segments), 3)
        for i, seg in enumerate(segments):
            self.assertEqual(seg["start"], float(i))
            self.assertEqual(seg["speaker"], "Unknown")

    def test_resolve_character_name_handles_alias(self):
        with patch.object(config_module.Config, "MODELS_DIR", self.tmp_path):
            extractor = CharacterProfileExtractor()

            character_lookup = {
                "Furnax": Character(name="Furnax", player="Companion", race="", class_name=""),
                "Sha'ek Mindfa'ek": Character(name="Sha'ek Mindfa'ek", player="Player", race="", class_name="", aliases=["Sha'ek"]),
            }

            resolved = extractor._resolve_character_name(
                "Sha'ek",
                character_lookup,
            )
            self.assertEqual(resolved, "Sha'ek Mindfa'ek")

    def test_resolve_character_name_fuzzy(self):
        """Test fuzzy resolution logic for unusual names (BUG-20251102-48)."""
        extractor = CharacterProfileExtractor()

        party_chars = {
            "K'th'lar": Character(name="K'th'lar", player="P1", race="", class_name=""),
            "Jean-Luc": Character(name="Jean-Luc", player="P2", race="", class_name=""),
            "The Great 790": Character(name="The Great 790", player="P3", race="", class_name="", aliases=["790", "Seven-Ninety"]),
            "M & M": Character(name="M & M", player="P4", race="", class_name="", aliases=["MnM"]),
        }

        # Exact
        self.assertEqual(extractor._resolve_character_name("K'th'lar", party_chars), "K'th'lar")
        # Case Insensitive
        self.assertEqual(extractor._resolve_character_name("JEAN-LUC", party_chars), "Jean-Luc")
        # Alias
        self.assertEqual(extractor._resolve_character_name("790", party_chars), "The Great 790")

        # Fuzzy / Simplified Matching
        self.assertEqual(extractor._resolve_character_name("M&M", party_chars), "M & M")
        self.assertEqual(extractor._resolve_character_name("M & M", party_chars), "M & M")

    def test_parse_complex_dialogue_lines(self):
        """Test parsing of unusual dialogue patterns (BUG-20251102-48)."""
        extractor = CharacterProfileExtractor()

        transcript_text = """[00:01:00] K'th'lar the Vile: I am ready.
[00:01:10] Dr. Jean-Luc: Status report: Critical.
[00:01:20] 790: [Protocol initiated] Scanning...
[00:01:30] M & M: We are one.
[00:01:50] Unknown Entity: You: Me. We are the same.
[00:02:00] No Timestamp Speaker: Just talking here.
"""
        transcript_path = self.tmp_path / "complex_transcript.txt"
        transcript_path.write_text(transcript_text, encoding="utf-8")

        segments = extractor._parse_plaintext_transcript(transcript_path)

        self.assertEqual(len(segments), 6)

        # 1. K'th'lar the Vile
        self.assertEqual(segments[0]['speaker'], "K'th'lar the Vile")
        self.assertEqual(segments[0]['text'], "I am ready.")
        self.assertEqual(segments[0]['start'], 60.0)

        # 2. Dr. Jean-Luc (Colon in message)
        self.assertEqual(segments[1]['speaker'], "Dr. Jean-Luc")
        self.assertEqual(segments[1]['text'], "Status report: Critical.")

        # 3. 790 (Numeric name + bracket in message)
        self.assertEqual(segments[2]['speaker'], "790")
        self.assertEqual(segments[2]['text'], "[Protocol initiated] Scanning...")

        # 4. M & M (Special chars in name)
        self.assertEqual(segments[3]['speaker'], "M & M")
        self.assertEqual(segments[3]['text'], "We are one.")

        # 5. Unknown Entity (Multiple colons)
        self.assertEqual(segments[4]['speaker'], "Unknown Entity")
        self.assertEqual(segments[4]['text'], "You: Me. We are the same.")

        # 6. No Timestamp
        self.assertEqual(segments[5]['speaker'], "No Timestamp Speaker")
        self.assertEqual(segments[5]['text'], "Just talking here.")

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
        self.assertIn("Rolled natural 20", formatted)
        self.assertIn("01:23:45", formatted)
        self.assertIn("goblin chief", formatted)

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
        self.assertIn('"', formatted)
        self.assertIn("abandon", formatted)
        self.assertIn("02:15:30", formatted)

    def test_has_updates_with_data(self):
        extractor = CharacterProfileExtractor()
        extracted = ExtractedCharacterData(
            character_name="Thorin",
            notable_actions=["Did something"],
        )

        self.assertTrue(extractor._has_updates(extracted))

    def test_has_updates_empty(self):
        extractor = CharacterProfileExtractor()
        extracted = ExtractedCharacterData(character_name="Thorin")

        self.assertFalse(extractor._has_updates(extracted))

    def test_batch_extract_requires_party_config(self):
        extractor = CharacterProfileExtractor()
        profile_mgr = CharacterProfileManager()
        party_mgr = PartyConfigManager()

        transcript_path = self.tmp_path / "temp_transcript.txt"
        transcript_path.write_text("[00:01:00] Thorin: I attack!\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "not found"):
            extractor.batch_extract_and_update(
                transcript_path=transcript_path,
                party_id="nonexistent_party",
                session_id="test_session",
                profile_manager=profile_mgr,
                party_manager=party_mgr,
            )

    def test_extracted_character_data_initialization(self):
        data = ExtractedCharacterData(character_name="Thorin")

        self.assertEqual(data.character_name, "Thorin")
        self.assertEqual(data.notable_actions, [])
        self.assertEqual(data.items_acquired, [])
        self.assertEqual(data.memorable_quotes, [])
        self.assertEqual(data.character_development, [])

    def test_batch_extract_updates_profiles(self):
        party_config_path = self.tmp_path / "parties.json"
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

        with patch.object(config_module.Config, "MODELS_DIR", self.tmp_path):
            party_mgr = PartyConfigManager(config_file=party_config_path)
            profiles_dir = self.tmp_path / "profiles"
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

            # Setup the specific return value for this test call
            self.mock_extractor_instance.extract_profile_updates.return_value = batch

            extractor = CharacterProfileExtractor() # Uses the patched class from setUp

            transcript_path = self.tmp_path / "session.txt"
            transcript_path.write_text("[00:10:00] Thorin: For the Seekers!\n", encoding="utf-8")

            results = extractor.batch_extract_and_update(
                transcript_path=transcript_path,
                party_id="party_alpha",
                session_id="session_123",
                profile_manager=profile_mgr,
                party_manager=party_mgr,
                campaign_id="campaign_xyz",
            )

            self.assertIn("Thorin", results)
            extracted = results["Thorin"]
            self.assertTrue(extracted.notable_actions)

            profile = profile_mgr.get_profile("Thorin")
            self.assertIsNotNone(profile)
            self.assertTrue(any("dragon" in action.description for action in profile.notable_actions))
            self.assertIn("session_123", profile.sessions_appeared)
            self.assertEqual(profile.total_sessions, len(profile.sessions_appeared))
            self.assertEqual(profile.campaign_id, "campaign_xyz")
