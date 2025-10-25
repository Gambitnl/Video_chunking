import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import os
import json
from src.character_profile import CharacterProfileManager, CharacterProfile, ProfileUpdate

class TestCharacterProfileManager(unittest.TestCase):

    def setUp(self):
        self.test_profiles_dir = Path('test_profiles')
        self.test_profiles_dir.mkdir(exist_ok=True)
        self.manager = CharacterProfileManager(profiles_dir=self.test_profiles_dir)

    def tearDown(self):
        for f in self.test_profiles_dir.glob('*.json'):
            os.remove(f)
        os.rmdir(self.test_profiles_dir)

    def test_merge_updates(self):
        """Test that merge_updates correctly adds new items to a character profile."""
        # Arrange
        profile = CharacterProfile(name='Thorin', player='Alice', race='Dwarf', class_name='Fighter')
        self.manager.add_profile('Thorin', profile)

        updates = {
            'notable_actions': [ProfileUpdate(character='Thorin', category='Critical Actions', type='any', content='A new action.', timestamp='s2', confidence=0.9, context='')],
            'memorable_quotes': [ProfileUpdate(character='Thorin', category='Memorable Quotes', type='any', content='A new quote.', timestamp='s2', confidence=0.9, context='')]
        }

        # Act
        updated_profile = self.manager.merge_updates('Thorin', updates)

        # Assert
        self.assertIsNotNone(updated_profile)
        self.assertEqual(len(updated_profile.notable_actions), 1)
        self.assertEqual(updated_profile.notable_actions[0].description, 'A new action.')
        self.assertEqual(len(updated_profile.memorable_quotes), 1)
        self.assertEqual(updated_profile.memorable_quotes[0].quote, 'A new quote.')

if __name__ == '__main__':
    unittest.main()
