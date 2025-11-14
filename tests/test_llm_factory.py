"""Tests for OllamaClientFactory."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.llm_factory import (
    OllamaClientFactory,
    OllamaConfig,
    OllamaConnectionError
)


class TestOllamaConfig:
    """Test OllamaConfig dataclass."""

    def test_default_values(self):
        """Test default configuration."""
        config = OllamaConfig()
        assert config.host == "http://localhost:11434"
        assert config.timeout == 30

    def test_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            "host": "http://remote:11434",
            "timeout": 60
        }
        config = OllamaConfig.from_dict(config_dict)

        assert config.host == "http://remote:11434"
        assert config.timeout == 60

    def test_from_dict_empty(self):
        """Test creating config from empty dictionary."""
        config = OllamaConfig.from_dict({})
        assert config.host == "http://localhost:11434"

    def test_from_dict_partial(self):
        """Test creating config with partial dictionary."""
        config_dict = {"host": "http://custom:11434"}
        config = OllamaConfig.from_dict(config_dict)

        assert config.host == "http://custom:11434"
        assert config.timeout == 30  # Default


class TestOllamaClientFactory:
    """Test OllamaClientFactory class."""

    @pytest.fixture
    def factory(self):
        """Create factory instance."""
        return OllamaClientFactory()

    def test_create_client_default_config(self, factory):
        """Test creating client with default configuration."""
        with patch('ollama.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.list.return_value = {'models': []}
            mock_client_class.return_value = mock_client

            client = factory.create_client(test_connection=False)

            assert client == mock_client
            mock_client_class.assert_called_once_with(
                host="http://localhost:11434",
                timeout=30
            )

    def test_create_client_custom_config(self, factory):
        """Test creating client with custom configuration."""
        with patch('ollama.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.list.return_value = {'models': []}
            mock_client_class.return_value = mock_client

            config = OllamaConfig(host="http://custom:11434", timeout=60)
            client = factory.create_client(config, test_connection=False)

            mock_client_class.assert_called_once_with(
                host="http://custom:11434",
                timeout=60
            )

    def test_create_client_with_connection_test(self, factory):
        """Test that connection is tested when requested."""
        with patch('ollama.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.list.return_value = {'models': [{'name': 'llama2'}]}
            mock_client_class.return_value = mock_client

            client = factory.create_client(test_connection=True)

            # Should have called list() to test connection
            mock_client.list.assert_called_once()

    def test_create_client_connection_failure(self, factory):
        """Test that connection failure raises error."""
        with patch('ollama.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.list.side_effect = ConnectionError("Cannot connect")
            mock_client_class.return_value = mock_client

            with pytest.raises(OllamaConnectionError, match="Failed to connect"):
                factory.create_client(test_connection=True, max_retries=1)

    @patch('time.sleep')
    def test_connection_retry_logic(self, mock_sleep, factory):
        """Test that connection is retried with backoff."""
        with patch('ollama.Client') as mock_client_class:
            mock_client = Mock()
            # Fail twice, succeed on third attempt
            mock_client.list.side_effect = [
                ConnectionError("Fail 1"),
                ConnectionError("Fail 2"),
                {'models': []}
            ]
            mock_client_class.return_value = mock_client

            client = factory.create_client(test_connection=True, max_retries=3)

            # Should have retried
            assert mock_client.list.call_count == 3
            # Should have slept between retries (exponential backoff)
            assert mock_sleep.call_count == 2

    @patch('time.sleep')
    def test_exponential_backoff_timing(self, mock_sleep, factory):
        """Test that exponential backoff uses correct timing."""
        with patch('ollama.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.list.side_effect = [
                ConnectionError("Fail 1"),
                ConnectionError("Fail 2"),
                ConnectionError("Fail 3"),
                {'models': []}
            ]
            mock_client_class.return_value = mock_client

            client = factory.create_client(test_connection=True, max_retries=4)

            # Verify exponential backoff: 1s, 2s, 4s
            calls = mock_sleep.call_args_list
            assert len(calls) == 3
            assert calls[0][0][0] == 1  # 2^0 = 1
            assert calls[1][0][0] == 2  # 2^1 = 2
            assert calls[2][0][0] == 4  # 2^2 = 4

    def test_client_caching(self, factory):
        """Test that clients are cached when requested."""
        with patch('ollama.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.list.return_value = {'models': []}
            mock_client_class.return_value = mock_client

            # Create client with caching
            client1 = factory.create_client(test_connection=False, use_cache=True)
            client2 = factory.create_client(test_connection=False, use_cache=True)

            # Should return same instance
            assert client1 is client2
            # Should only create client once
            assert mock_client_class.call_count == 1

    def test_cache_different_hosts(self, factory):
        """Test that different hosts get different cached clients."""
        with patch('ollama.Client') as mock_client_class:
            mock_client_class.return_value = Mock()

            config1 = OllamaConfig(host="http://host1:11434")
            config2 = OllamaConfig(host="http://host2:11434")

            client1 = factory.create_client(config1, test_connection=False, use_cache=True)
            client2 = factory.create_client(config2, test_connection=False, use_cache=True)

            # Should create two different clients
            assert mock_client_class.call_count == 2

    def test_cache_different_timeouts(self, factory):
        """Test that different timeouts create different cache entries."""
        with patch('ollama.Client') as mock_client_class:
            mock_client_class.return_value = Mock()

            config1 = OllamaConfig(host="http://localhost:11434", timeout=30)
            config2 = OllamaConfig(host="http://localhost:11434", timeout=60)

            client1 = factory.create_client(config1, test_connection=False, use_cache=True)
            client2 = factory.create_client(config2, test_connection=False, use_cache=True)

            # Should create two different clients (different timeouts)
            assert mock_client_class.call_count == 2

    def test_clear_cache(self, factory):
        """Test cache clearing."""
        factory._client_cache["key1"] = Mock()
        factory._client_cache["key2"] = Mock()

        factory.clear_cache()

        assert len(factory._client_cache) == 0

    def test_get_cache_stats(self, factory):
        """Test cache statistics."""
        factory._client_cache["host1:30"] = Mock()
        factory._client_cache["host2:30"] = Mock()

        stats = factory.get_cache_stats()

        assert stats["cached_clients"] == 2
        assert "host1:30" in stats["hosts"]
        assert "host2:30" in stats["hosts"]

    def test_get_cache_stats_empty(self, factory):
        """Test cache statistics when empty."""
        stats = factory.get_cache_stats()

        assert stats["cached_clients"] == 0
        assert stats["hosts"] == []

    def test_model_availability_check(self, factory):
        """Test checking if specific model is available."""
        mock_client = Mock()
        mock_client.list.return_value = {
            'models': [
                {'name': 'llama2'},
                {'name': 'mistral'}
            ]
        }

        assert factory.test_model_available(mock_client, 'llama2') is True
        assert factory.test_model_available(mock_client, 'mistral') is True
        assert factory.test_model_available(mock_client, 'gpt-4') is False

    def test_model_availability_check_error(self, factory):
        """Test model availability check handles errors gracefully."""
        mock_client = Mock()
        mock_client.list.side_effect = Exception("API Error")

        # Should return False on error, not raise
        assert factory.test_model_available(mock_client, 'llama2') is False

    def test_model_count_logging(self, factory):
        """Test that successful connection logs model count."""
        with patch('ollama.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.list.return_value = {
                'models': [
                    {'name': 'llama2'},
                    {'name': 'mistral'},
                    {'name': 'codellama'}
                ]
            }
            mock_client_class.return_value = mock_client

            # This should log that 3 models are available
            client = factory.create_client(test_connection=True)
            assert client == mock_client

    def test_create_client_failure(self, factory):
        """Test that client creation failure is handled."""
        with patch('ollama.Client') as mock_client_class:
            mock_client_class.side_effect = Exception("Connection refused")

            with pytest.raises(OllamaConnectionError, match="Failed to create client"):
                factory.create_client(test_connection=False)

    def test_no_retry_when_test_disabled(self, factory):
        """Test that no retries happen when connection testing is disabled."""
        with patch('ollama.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            client = factory.create_client(test_connection=False)

            # Should not have called list() at all
            mock_client.list.assert_not_called()

    def test_custom_logger(self):
        """Test that custom logger is used."""
        import logging
        custom_logger = logging.getLogger("custom")
        factory = OllamaClientFactory(logger=custom_logger)

        assert factory.logger == custom_logger

    def test_connection_test_all_retries_fail(self, factory):
        """Test that error is raised when all retries fail."""
        with patch('ollama.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.list.side_effect = ConnectionError("Cannot connect")
            mock_client_class.return_value = mock_client

            with pytest.raises(OllamaConnectionError) as exc_info:
                factory.create_client(test_connection=True, max_retries=2)

            # Verify error message contains retry count
            assert "after 2 attempts" in str(exc_info.value)

    def test_model_list_non_dict_response(self, factory):
        """Test handling of non-dict response from list()."""
        with patch('ollama.Client') as mock_client_class:
            mock_client = Mock()
            # Some edge case where list() doesn't return a dict
            mock_client.list.return_value = []
            mock_client_class.return_value = mock_client

            # Should handle gracefully
            client = factory.create_client(test_connection=True)
            assert client == mock_client

    def test_model_to_check_parameter(self, factory):
        """Test model_to_check parameter avoids redundant API calls."""
        with patch('ollama.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.list.return_value = {
                'models': [{'name': 'llama2'}, {'name': 'mistral'}]
            }
            mock_client_class.return_value = mock_client

            # Create client with model check
            client = factory.create_client(
                test_connection=True,
                model_to_check='llama2'
            )

            # Should only call list() once (not twice)
            assert mock_client.list.call_count == 1

    def test_model_to_check_not_available(self, factory):
        """Test warning when requested model is not available."""
        with patch('ollama.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.list.return_value = {
                'models': [{'name': 'llama2'}]
            }
            mock_client_class.return_value = mock_client

            # Create client checking for unavailable model
            client = factory.create_client(
                test_connection=True,
                model_to_check='gpt-4'
            )

            # Should still return client (just logs warning)
            assert client == mock_client

    def test_ollama_not_installed(self, factory):
        """Test that ImportError is raised when ollama is not installed."""
        # Mock the import of ollama to raise ImportError
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == 'ollama':
                raise ImportError("No module named 'ollama'")
            return real_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            with pytest.raises(ImportError, match="ollama package is required"):
                factory.create_client()
