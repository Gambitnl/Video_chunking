import unittest
import sys
from unittest.mock import patch, MagicMock
from src.langchain.llm_factory import LLMFactory

class TestLLMFactoryFallback(unittest.TestCase):

    def test_ollama_fallback(self):
        """Test fallback to langchain_community when langchain_ollama is missing."""

        # Mock Config
        with patch('src.langchain.llm_factory.Config') as MockConfig:
            MockConfig.LLM_BACKEND = "ollama"
            MockConfig.OLLAMA_MODEL = "test-model"
            MockConfig.OLLAMA_BASE_URL = "http://test:11434"

            # We need to mock 'langchain_community.llms' so we can check if Ollama was called from there.
            mock_community_llms = MagicMock()
            mock_ollama_class = MagicMock()
            mock_community_llms.Ollama = mock_ollama_class

            # Simulate langchain_ollama raising ImportError
            with patch.dict(sys.modules, {
                'langchain_ollama': None,
                'langchain_community.llms': mock_community_llms
            }):
                llm = LLMFactory.create_llm(provider="ollama")

                # Verify fallback was used
                mock_ollama_class.assert_called_once()
                _, kwargs = mock_ollama_class.call_args
                self.assertEqual(kwargs['model'], "test-model")
                self.assertEqual(kwargs['base_url'], "http://test:11434")
                self.assertEqual(llm, mock_ollama_class.return_value)

    def test_ollama_primary_success(self):
        """Test that langchain_ollama is used when available."""

        with patch('src.langchain.llm_factory.Config') as MockConfig:
            MockConfig.LLM_BACKEND = "ollama"
            MockConfig.OLLAMA_MODEL = "test-model"
            MockConfig.OLLAMA_BASE_URL = "http://test:11434"

            mock_ollama_pkg = MagicMock()
            mock_ollama_llm = MagicMock()
            mock_ollama_pkg.OllamaLLM = mock_ollama_llm

            mock_community_llms = MagicMock()
            mock_community_ollama = MagicMock()
            mock_community_llms.Ollama = mock_community_ollama

            with patch.dict(sys.modules, {
                'langchain_ollama': mock_ollama_pkg,
                'langchain_community.llms': mock_community_llms
            }):
                llm = LLMFactory.create_llm(provider="ollama")

                # Verify primary was used
                mock_ollama_llm.assert_called_once()
                # Verify fallback was NOT used
                mock_community_ollama.assert_not_called()
