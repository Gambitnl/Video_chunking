"""
Client for interacting with a Large Language Model.
"""
from .config import Config
from .logger import get_logger
from .llm_factory import OllamaClientFactory, OllamaConfig, OllamaConnectionError

class LlmClient:
    """Client for interacting with an LLM."""

    def __init__(self, model: str = None, base_url: str = None):
        self.model = model or Config.OLLAMA_MODEL
        self.base_url = base_url or Config.OLLAMA_BASE_URL
        self.logger = get_logger("llm_client")

        # Initialize Ollama client using factory
        factory = OllamaClientFactory(logger=self.logger)
        ollama_config = OllamaConfig(
            host=self.base_url,
            timeout=30
        )

        try:
            self.client = factory.create_client(
                config=ollama_config,
                test_connection=True,
                max_retries=3,
                use_cache=True  # LlmClient can benefit from caching
            )
        except OllamaConnectionError as e:
            raise RuntimeError(
                f"Could not connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running.\n"
                f"Install: https://ollama.ai\n"
                f"Error: {e}"
            ) from e

    def generate(self, prompt: str, options: dict = None) -> dict:
        """Generate text from the LLM."""
        return self.client.generate(
            model=self.model,
            prompt=prompt,
            options=options or {},
        )

