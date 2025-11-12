"""
Factory for creating and managing Ollama LLM clients.

This module centralizes Ollama client initialization, connection testing,
and error handling across the application.
"""

import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class OllamaConfig:
    """Configuration for Ollama client."""

    host: str = "http://localhost:11434"
    timeout: int = 30

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "OllamaConfig":
        """Create config from dictionary."""
        return cls(
            host=config.get("host", "http://localhost:11434"),
            timeout=config.get("timeout", 30)
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

        # Or with custom config and model checking
        config = OllamaConfig(host="http://remote-server:11434")
        client = factory.create_client(config, model_to_check="llama2")
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the factory.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self._client_cache: Dict[str, Any] = {}

    def create_client(
        self,
        config: Optional[OllamaConfig] = None,
        test_connection: bool = True,
        max_retries: int = 3,
        use_cache: bool = False,
        model_to_check: Optional[str] = None
    ) -> Any:
        """
        Create an Ollama client with optional connection testing.

        Args:
            config: Client configuration (uses defaults if None)
            test_connection: If True, test connection before returning
            max_retries: Number of connection test retries
            use_cache: If True, reuse existing client for same host
            model_to_check: If provided, check if this model is available

        Returns:
            Configured and tested ollama.Client instance

        Raises:
            OllamaConnectionError: If connection test fails after retries
            ImportError: If ollama package is not installed
        """
        # Lazy import of ollama - only when actually creating a client
        try:
            import ollama
        except ImportError:
            raise ImportError(
                "ollama package is required for OllamaClientFactory. "
                "Install with: pip install ollama"
            )

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
        available_models = None
        if test_connection:
            available_models = self._test_connection(client, config.host, max_retries)

        # Check model availability if requested (using already-fetched models)
        if model_to_check:
            if available_models is None:
                # If we didn't test connection, fetch models now
                available_models = self._fetch_available_models(client)

            if available_models is not None and model_to_check not in available_models:
                self.logger.warning(
                    f"Model '{model_to_check}' may not be available. "
                    f"Available models: {', '.join(available_models)}. "
                    "Classification may fail."
                )

        # Cache if requested
        if use_cache:
            self._client_cache[cache_key] = client

        return client

    def _test_connection(
        self,
        client: Any,
        host: str,
        max_retries: int
    ) -> Optional[List[str]]:
        """
        Test connection to Ollama server with retries.

        Args:
            client: Client to test
            host: Host being connected to (for logging)
            max_retries: Number of retry attempts

        Returns:
            List of available model names, or None if models couldn't be fetched

        Raises:
            OllamaConnectionError: If all retries fail
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                self.logger.debug(f"Testing connection to {host} (attempt {attempt + 1}/{max_retries})")

                # Try to list models - this tests the connection
                models = client.list()

                # Success! Extract model names
                available_models = self._extract_model_names(models)
                model_count = len(available_models)
                self.logger.info(
                    f"Successfully connected to {host} "
                    f"({model_count} models available)"
                )
                return available_models

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

    def _fetch_available_models(self, client: Any) -> Optional[List[str]]:
        """
        Fetch available models from the server.

        Args:
            client: Ollama client

        Returns:
            List of available model names, or None on error
        """
        try:
            models = client.list()
            return self._extract_model_names(models)
        except Exception as e:
            self.logger.error(f"Failed to fetch available models: {e}")
            return None

    def _extract_model_names(self, models_response: Any) -> List[str]:
        """
        Extract model names from the API response.

        Args:
            models_response: Response from client.list()

        Returns:
            List of model names
        """
        if isinstance(models_response, dict):
            return [m['name'] for m in models_response.get('models', [])]
        return []

    def test_model_available(
        self,
        client: Any,
        model_name: str
    ) -> bool:
        """
        Test if a specific model is available on the server.

        Note: Prefer using the model_to_check parameter in create_client()
        to avoid redundant API calls.

        Args:
            client: Ollama client
            model_name: Name of model to check

        Returns:
            True if model is available, False otherwise
        """
        available_models = self._fetch_available_models(client)

        if available_models is None:
            return False

        is_available = model_name in available_models

        if is_available:
            self.logger.debug(f"Model '{model_name}' is available")
        else:
            self.logger.warning(
                f"Model '{model_name}' not found. "
                f"Available models: {', '.join(available_models)}"
            )

        return is_available

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
