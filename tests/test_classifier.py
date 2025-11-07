
import pytest
from unittest.mock import patch, MagicMock, mock_open

# Mock the config before other imports
@pytest.fixture(autouse=True)
def patched_config():
    with patch('src.classifier.Config') as MockConfig:
        MockConfig.LLM_BACKEND = 'ollama'
        MockConfig.OLLAMA_MODEL = 'test-model'
        MockConfig.OLLAMA_FALLBACK_MODEL = None
        MockConfig.OLLAMA_BASE_URL = 'http://localhost:11434'
        # Create a dummy prompt file path
        MockConfig.PROJECT_ROOT.return_value = MagicMock()
        type(MockConfig).PROJECT_ROOT = MagicMock()
        yield MockConfig

from src.classifier import ClassifierFactory, OllamaClassifier, ClassificationResult

@pytest.fixture
def mock_ollama_client():
    """Fixture to mock the ollama.Client and its methods."""
    with patch('ollama.Client') as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.list.return_value = True  # Simulate successful connection
        yield mock_instance

@pytest.fixture
def mock_prompt_file():
    """Fixture to mock the prompt file reading."""
    prompt_content = """
    Characters: {char_list}
    Players: {player_list}
    --- Context ---
    Previous: {prev_text}
    Current: {current_text}
    Next: {next_text}
    """
    with patch('builtins.open', mock_open(read_data=prompt_content)) as mock_file:
        yield mock_file

class TestClassifierFactory:
    def test_create_ollama_backend(self, mock_ollama_client, mock_prompt_file):
        classifier = ClassifierFactory.create(backend='ollama')
        assert isinstance(classifier, OllamaClassifier)

    def test_create_openai_backend_raises_error(self):
        with pytest.raises(NotImplementedError):
            ClassifierFactory.create(backend='openai')

    def test_create_unknown_backend_raises_error(self):
        with pytest.raises(ValueError, match="Unknown classifier backend: unknown"):
            ClassifierFactory.create(backend='unknown')

class TestOllamaClassifier:

    def test_init_raises_error_on_connection_failure(self, mock_prompt_file):
        with patch('ollama.Client') as MockClient:
            MockClient.return_value.list.side_effect = Exception("Connection failed")
            with pytest.raises(RuntimeError, match="Could not connect to Ollama"):
                OllamaClassifier()

    def test_init_raises_error_on_prompt_not_found(self, mock_ollama_client):
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.side_effect = FileNotFoundError
            with pytest.raises(RuntimeError, match="Prompt file not found"):
                OllamaClassifier()

    def test_build_prompt(self, mock_ollama_client, mock_prompt_file):
        classifier = OllamaClassifier()
        prompt = classifier._build_prompt("prev", "current", "next", ["C1"], ["P1"])
        assert "Characters: C1" in prompt
        assert "Players: P1" in prompt
        assert "Current: current" in prompt

    @pytest.mark.parametrize("response_str, expected_class, expected_conf, expected_char", [
        ("Classificatie: IC\nReden: In character\nVertrouwen: 0.9\nPersonage: Aragorn", "IC", 0.9, "Aragorn"),
        ("Classificatie: OOC\nReden: Out of character", "OOC", 0.5, None),
        ("Classificatie: MIXED\nVertrouwen: 0.7", "MIXED", 0.7, None),
        ("Invalid response", "IC", 0.5, None), # Test fallback
        ("Classificatie: INVALID\nVertrouwen: 1.2", "IC", 1.0, None), # Test invalid values
    ])
    def test_parse_response(self, mock_ollama_client, mock_prompt_file, response_str, expected_class, expected_conf, expected_char):
        classifier = OllamaClassifier()
        result = classifier._parse_response(response_str, 0)
        assert isinstance(result, ClassificationResult)
        assert result.classification == expected_class
        assert result.confidence == pytest.approx(expected_conf)
        assert result.character == expected_char

    def test_classify_segments(self, mock_ollama_client, mock_prompt_file):
        # Arrange
        classifier = OllamaClassifier()
        mock_response = {'response': "Classificatie: IC\nVertrouwen: 0.8\nPersonage: TestChar"}
        mock_ollama_client.generate.return_value = mock_response

        segments = [
            {'text': 'Segment 1'},
            {'text': 'Segment 2'},
        ]

        # Act
        results = classifier.classify_segments(segments, ["TestChar"], ["TestPlayer"])

        # Assert
        assert mock_ollama_client.generate.call_count == 2
        assert len(results) == 2
        assert results[0].classification == "IC"
        assert results[0].confidence == 0.8
        assert results[0].character == "TestChar"
        assert results[1].segment_index == 1

    def test_classify_retries_with_low_vram_on_memory_error(self, mock_ollama_client, mock_prompt_file):
        classifier = OllamaClassifier()
        mock_ollama_client.generate.side_effect = [
            Exception("memory layout cannot be allocated (status code: 500)"),
            {'response': "Classificatie: OOC\nVertrouwen: 0.6\nPersonage: N/A"}
        ]

        segments = [{'text': 'Segment 1'}]
        results = classifier.classify_segments(segments, [], [])

        assert len(results) == 1
        assert results[0].classification == "OOC"
        assert mock_ollama_client.generate.call_count == 2
        first_call = mock_ollama_client.generate.call_args_list[0]
        second_call = mock_ollama_client.generate.call_args_list[1]
        assert first_call.kwargs['model'] == 'test-model'
        assert second_call.kwargs['model'] == 'test-model'
        assert second_call.kwargs['options']['low_vram'] is True

    def test_classify_retries_with_fallback_if_configured(self, mock_ollama_client, mock_prompt_file, patched_config):
        patched_config.OLLAMA_FALLBACK_MODEL = 'test-fallback'
        classifier = OllamaClassifier()
        mock_ollama_client.generate.side_effect = [
            Exception("memory layout cannot be allocated (status code: 500)"),
            Exception("still running low vram"),
            {'response': "Classificatie: OOC\nVertrouwen: 0.6\nPersonage: N/A"}
        ]

        segments = [{'text': 'Segment 1'}]
        results = classifier.classify_segments(segments, [], [])

        assert len(results) == 1
        assert results[0].classification == "OOC"
        assert mock_ollama_client.generate.call_count == 3
        fallback_call = mock_ollama_client.generate.call_args_list[2]
        assert fallback_call.kwargs['model'] == 'test-fallback'

    def test_classify_defaults_when_retries_fail(self, mock_ollama_client, mock_prompt_file):
        classifier = OllamaClassifier()
        mock_ollama_client.generate.side_effect = [
            Exception("memory layout cannot be allocated"),
            Exception("still failing")
        ]

        segments = [{'text': 'Segment 1'}]
        results = classifier.classify_segments(segments, [], [])

        assert len(results) == 1
        assert results[0].classification == "IC"
        assert results[0].confidence == 0.5
        assert "defaulted to IC" in results[0].reasoning
        assert mock_ollama_client.generate.call_count == 2


class TestClassificationResult:
    def test_to_dict(self):
        result = ClassificationResult(
            segment_index=0, classification="IC", confidence=0.9, reasoning="Test reason", character="Aragorn"
        )
        expected_dict = {
            "segment_index": 0,
            "classification": "IC",
            "confidence": 0.9,
            "reasoning": "Test reason",
            "character": "Aragorn",
        }
        assert result.to_dict() == expected_dict

    def test_from_dict(self):
        data = {
            "segment_index": 0,
            "classification": "IC",
            "confidence": 0.9,
            "reasoning": "Test reason",
            "character": "Aragorn",
        }
        result = ClassificationResult.from_dict(data)
        assert result.segment_index == 0
        assert result.classification == "IC"
        assert result.confidence == 0.9
        assert result.reasoning == "Test reason"
        assert result.character == "Aragorn"

    def test_from_dict_no_character(self):
        data = {
            "segment_index": 1,
            "classification": "OOC",
            "confidence": 0.7,
            "reasoning": "Test reason OOC",
        }
        result = ClassificationResult.from_dict(data)
        assert result.segment_index == 1
        assert result.classification == "OOC"
        assert result.confidence == 0.7
        assert result.reasoning == "Test reason OOC"
        assert result.character is None
