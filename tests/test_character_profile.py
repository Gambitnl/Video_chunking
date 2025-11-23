import unittest
from pathlib import Path
import os
import json
import shutil
from dataclasses import asdict
from src.character_profile import (
    CharacterProfileManager,
    CharacterProfile,
    ProfileUpdate,
    CharacterAction,
    CharacterItem,
    CharacterRelationship,
    CharacterDevelopment,
    CharacterQuote
)

class TestCharacterProfilePersistence(unittest.TestCase):

    def setUp(self):
        self.test_profiles_dir = Path('test_profiles_persistence')
        if self.test_profiles_dir.exists():
            shutil.rmtree(self.test_profiles_dir)
        self.test_profiles_dir.mkdir(exist_ok=True)
        self.manager = CharacterProfileManager(profiles_dir=self.test_profiles_dir)

    def tearDown(self):
        if self.test_profiles_dir.exists():
            shutil.rmtree(self.test_profiles_dir)

    def test_full_profile_persistence(self):
        """
        Verify that a CharacterProfile with ALL fields populated is saved and loaded
        without data loss.
        """
        # Create a rich profile
        original_profile = CharacterProfile(
            name="K'th'lar-99",
            player="The Tester",
            race="Warforged",
            class_name="Artificer",
            level=5,
            description="A shiny metal robot with a heart of gold.",
            personality="Calculating but kind.",
            backstory="Forged in the fires of Mount Doom (copyright infringement intended).",
            appearance="Chrome plated.",
            aliases=["K-Unit", "Tin Man"],
            campaign_id="camp_123",
            campaign_name="The Test Campaign",
            first_session="session_01",
            last_updated="2023-01-01T12:00:00",
            total_sessions=10,
            current_goals=["Find the wizard", "Get oil"],
            completed_goals=["Survive level 1"],
            dm_notes="Secretly a mimic.",
            player_notes="I need more spell slots.",
            sessions_appeared=["session_01", "session_05"]
        )

        # Add complex nested objects
        original_profile.notable_actions.append(CharacterAction(
            session="session_01",
            timestamp="12:00",
            description="Saved the cat",
            type="heroic"
        ))
        original_profile.inventory.append(CharacterItem(
            name="Sword of Testing",
            description="Sharp",
            session_acquired="session_02",
            category="weapon"
        ))
        original_profile.relationships.append(CharacterRelationship(
            name="Bob",
            relationship_type="friend",
            description="Best bud",
            first_met="session_01"
        ))
        original_profile.development_notes.append(CharacterDevelopment(
            session="session_03",
            note="Realized he has a soul",
            category="personality"
        ))
        original_profile.memorable_quotes.append(CharacterQuote(
            session="session_04",
            quote="I'll be back.",
            context="Leaving the tavern"
        ))

        # Save
        self.manager.add_profile(original_profile.name, original_profile)

        # Force reload from disk by re-instantiating the manager or manually loading
        # (The manager loads on init, so let's make a new one pointing to the same dir)
        new_manager = CharacterProfileManager(profiles_dir=self.test_profiles_dir)
        loaded_profile = new_manager.get_profile(original_profile.name)

        self.assertIsNotNone(loaded_profile, "Profile failed to load.")

        # Compare dictionaries to ensure deep equality
        # We assume order is preserved in lists
        original_dict = asdict(original_profile)
        loaded_dict = asdict(loaded_profile)

        # Remove 'last_updated' from comparison as saving might update it automatically
        # (Though we manually set it, add_profile -> _save_single_profile updates it)
        if 'last_updated' in original_dict: del original_dict['last_updated']
        if 'last_updated' in loaded_dict: del loaded_dict['last_updated']

        self.assertEqual(original_dict, loaded_dict)

    def test_merge_updates(self):
        """Test that merge_updates correctly adds new items to a character profile."""
        profile = CharacterProfile(name='Thorin', player='Alice', race='Dwarf', class_name='Fighter')
        self.manager.add_profile('Thorin', profile)

        updates = {
            'notable_actions': [ProfileUpdate(character='Thorin', category='notable_actions', content='A new action.', timestamp='01:00')],
            'memorable_quotes': [ProfileUpdate(character='Thorin', category='memorable_quotes', content='A new quote.', quote='A new quote.', timestamp='01:00')]
        }

        updated_profile = self.manager.merge_updates('Thorin', updates)

        self.assertIsNotNone(updated_profile)
        self.assertEqual(len(updated_profile.notable_actions), 1)
        self.assertEqual(updated_profile.notable_actions[0].description, 'A new action.')
        self.assertEqual(len(updated_profile.memorable_quotes), 1)
        self.assertEqual(updated_profile.memorable_quotes[0].quote, 'A new quote.')

if __name__ == '__main__':
    unittest.main()
