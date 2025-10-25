"""
Client for interacting with a Large Language Model.
"""
from .config import Config

class LlmClient:
    """Client for interacting with an LLM."""

    def __init__(self, model: str = None, base_url: str = None):
        import ollama

        self.model = model or Config.OLLAMA_MODEL
        self.base_url = base_url or Config.OLLAMA_BASE_URL

        self.client = ollama.Client(host=self.base_url)

        try:
            self.client.list()
        except Exception as e:
            raise RuntimeError(
                f"Could not connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running.\n"
                f"Install: https://ollama.ai\n"
                f"Error: {e}"
            )

    def generate(self, prompt: str, options: dict = None) -> dict:
        """Generate text from the LLM."""
        return self.client.generate(
            model=self.model,
            prompt=prompt,
            options=options or {},
        )

