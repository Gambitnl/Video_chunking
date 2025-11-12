"""
Factory for creating and managing Ollama LLM clients.

This module centralizes Ollama client initialization, connection testing,
and error handling across the application.
"""

import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

try:
    import ollama
except ImportError:
    raise ImportError("ollama package is required. Install with: pip install ollama")


@dataclass
class OllamaConfig:
    """Configuration for Ollama client."""

    host: str = "http://localhost:11434"
    timeout: int = 30
    verify_ssl: bool = True

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "OllamaConfig":
        """Create config from dictionary."""
        return cls(
            host=config.get("host", "http://localhost:11434"),
            timeout=config.get("timeout", 30),
            verify_ssl=config.get("verify_ssl", True)
        )


class OllamaConnectionError(Exception):
    """Raised when cannot connect to Ollama server."""
    pass


class OllamaClientFactory:
    """
    Factory for creating Ollama clients with connection testing.

    Features:
    - Automatic connection testing
    - Retry logic with exponential backoff
    - Detailed error reporting
    - Optional client caching

    Usage:
        factory = OllamaClientFactory()
        client = factory.create_client()

        # Or with custom config
        config = OllamaConfig(host="http://remote-server:11434")
        client = factory.create_client(config)
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the factory.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self._client_cache: Dict[str, ollama.Client] = {}

    def create_client(
        self,
        config: Optional[OllamaConfig] = None,
        test_connection: bool = True,
        max_retries: int = 3,
        use_cache: bool = False
    ) -> ollama.Client:
        """
        Create an Ollama client with optional connection testing.

        Args:
            config: Client configuration (uses defaults if None)
            test_connection: If True, test connection before returning
            max_retries: Number of connection test retries
            use_cache: If True, reuse existing client for same host

        Returns:
            Configured and tested ollama.Client instance

        Raises:
            OllamaConnectionError: If connection test fails after retries
        """
        if config is None:
            config = OllamaConfig()

        # Check cache
        cache_key = f"{config.host}:{config.timeout}"
        if use_cache and cache_key in self._client_cache:
            self.logger.debug(f"Using cached client for {config.host}")
            return self._client_cache[cache_key]

        # Create client
        self.logger.info(f"Creating Ollama client for {config.host}")

        try:
            client = ollama.Client(
                host=config.host,
                timeout=config.timeout
            )
        except Exception as e:
            raise OllamaConnectionError(f"Failed to create client: {e}") from e

        # Test connection if requested
        if test_connection:
            self._test_connection(client, config.host, max_retries)

        # Cache if requested
        if use_cache:
            self._client_cache[cache_key] = client

        return client

    def _test_connection(
        self,
        client: ollama.Client,
        host: str,
        max_retries: int
    ) -> None:
        """
        Test connection to Ollama server with retries.

        Args:
            client: Client to test
            host: Host being connected to (for logging)
            max_retries: Number of retry attempts

        Raises:
            OllamaConnectionError: If all retries fail
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                self.logger.debug(f"Testing connection to {host} (attempt {attempt + 1}/{max_retries})")

                # Try to list models - this tests the connection
                models = client.list()

                # Success!
                model_count = len(models.get('models', [])) if isinstance(models, dict) else 0
                self.logger.info(
                    f"Successfully connected to {host} "
                    f"({model_count} models available)"
                )
                return

            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"Connection test failed (attempt {attempt + 1}/{max_retries}): {e}"
                )

                # Wait before retry (exponential backoff)
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    self.logger.debug(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)

        # All retries failed
        raise OllamaConnectionError(
            f"Failed to connect to Ollama at {host} after {max_retries} attempts. "
            f"Last error: {last_error}"
        ) from last_error

    def test_model_available(
        self,
        client: ollama.Client,
        model_name: str
    ) -> bool:
        """
        Test if a specific model is available on the server.

        Args:
            client: Ollama client
            model_name: Name of model to check

        Returns:
            True if model is available, False otherwise
        """
        try:
            models = client.list()
            available_models = [
                m['name'] for m in models.get('models', [])
            ] if isinstance(models, dict) else []

            is_available = model_name in available_models

            if is_available:
                self.logger.debug(f"Model '{model_name}' is available")
            else:
                self.logger.warning(
                    f"Model '{model_name}' not found. "
                    f"Available models: {', '.join(available_models)}"
                )

            return is_available

        except Exception as e:
            self.logger.error(f"Failed to check model availability: {e}")
            return False

    def clear_cache(self) -> None:
        """Clear the client cache."""
        self._client_cache.clear()
        self.logger.debug("Cleared client cache")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            "cached_clients": len(self._client_cache),
            "hosts": list(self._client_cache.keys())
        }
