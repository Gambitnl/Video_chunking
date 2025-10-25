import unittest
from unittest.mock import MagicMock
from src.profile_extractor import ProfileExtractor, ProfileUpdate
from src.config import Config
from src.character_profile import CharacterProfile, CharacterAction, CharacterQuote

class TestProfileExtractor(unittest.TestCase):

    def setUp(self):
        self.mock_llm_client = MagicMock()
        self.config = Config()
        self.extractor = ProfileExtractor(self.mock_llm_client, self.config)

    def test_extract_moments_success(self):
        """Test successful extraction of moments from a transcript."""
        # Arrange
        transcript = [
            {'classification': 'IC', 'start_time': '00:01:00', 'speaker': 'Thorin', 'text': 'I will take the watch.'},
            {'classification': 'OOC', 'start_time': '00:01:30', 'speaker': 'Alice', 'text': 'Pass the chips.'},
            {'classification': 'IC', 'start_time': '00:02:00', 'speaker': 'Elara', 'text': 'I cast a light spell.'},
        ]
        
        llm_response = {
            'response': '[{"character": "Thorin", "category": "Critical Actions", "type": "taking_watch", "content": "I will take the watch.", "timestamp": "00:01:00", "confidence": 0.8, "context": "The party is setting up camp."}]'
        }
        self.mock_llm_client.generate.return_value = llm_response

        # Act
        updates = self.extractor.extract_moments(transcript)

        # Assert
        self.assertEqual(len(updates), 1)
        self.assertIsInstance(updates[0], ProfileUpdate)
        self.assertEqual(updates[0].character, 'Thorin')
        self.assertEqual(updates[0].content, 'I will take the watch.')

    def test_extract_moments_invalid_json(self):
        """Test that an empty list is returned when the LLM provides invalid JSON."""
        # Arrange
        transcript = [
            {'classification': 'IC', 'start_time': '00:01:00', 'speaker': 'Thorin', 'text': 'I will take the watch.'},
        ]
        
        llm_response = {
            'response': 'This is not JSON'
        }
        self.mock_llm_client.generate.return_value = llm_response

        # Act
        updates = self.extractor.extract_moments(transcript)

        # Assert
        self.assertEqual(len(updates), 0)

    def test_suggest_updates_filters_duplicates(self):
        """Test that suggest_updates filters out duplicate moments."""
        # Arrange
        existing_profile = CharacterProfile(
            name='Thorin',
            player='Alice',
            race='Dwarf',
            class_name='Fighter',
            notable_actions=[CharacterAction(session='s1', description='A duplicate action.')],
            memorable_quotes=[CharacterQuote(session='s1', quote='A duplicate quote.')]
        )
        
        moments = [
            ProfileUpdate(character='Thorin', category='Critical Actions', type='any', content='A new action.', timestamp='s2', confidence=0.9, context=''),
            ProfileUpdate(character='Thorin', category='Critical Actions', type='any', content='A duplicate action.', timestamp='s2', confidence=0.9, context=''),
            ProfileUpdate(character='Thorin', category='Memorable Quotes', type='any', content='A new quote.', timestamp='s2', confidence=0.9, context=''),
            ProfileUpdate(character='Thorin', category='Memorable Quotes', type='any', content='A duplicate quote.', timestamp='s2', confidence=0.9, context=''),
        ]

        # Act
        suggestions = self.extractor.suggest_updates(moments, existing_profile)

        # Assert
        self.assertEqual(len(suggestions['notable_actions']), 1)
        self.assertEqual(suggestions['notable_actions'][0].content, 'A new action.')
        self.assertEqual(len(suggestions['memorable_quotes']), 1)
        self.assertEqual(suggestions['memorable_quotes'][0].content, 'A new quote.')

if __name__ == '__main__':
    unittest.main()
