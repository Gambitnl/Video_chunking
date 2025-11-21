import logging
from typing import Optional
from src.config import Config

logger = logging.getLogger(__name__)

class LLMFactory:
    """Factory for creating LangChain LLM instances."""

    @staticmethod
    def create_llm(provider: str = None, model_name: str = None):
        """
        Initialize the LLM based on provider configuration.

        Args:
            provider: LLM provider ('ollama' or 'openai'). Defaults to Config.LLM_BACKEND.
            model_name: Model name to use. Defaults to Config.OLLAMA_MODEL.

        Returns:
            A LangChain LLM instance.

        Raises:
            ValueError: If the provider is unsupported.
            RuntimeError: If required dependencies are missing.
        """
        provider = provider or Config.LLM_BACKEND
        model_name = model_name or Config.OLLAMA_MODEL

        try:
            if provider == "ollama":
                try:
                    from langchain_ollama import OllamaLLM
                    return OllamaLLM(
                        model=model_name,
                        base_url=Config.OLLAMA_BASE_URL
                    )
                except ImportError:
                    # Fallback to deprecated import
                    from langchain_community.llms import Ollama
                    return Ollama(
                        model=model_name,
                        base_url=Config.OLLAMA_BASE_URL
                    )
            elif provider == "openai":
                from langchain_community.llms import OpenAI
                return OpenAI(
                    model=model_name,
                    openai_api_key=Config.OPENAI_API_KEY
                )
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
        except ImportError as e:
            logger.error(f"Failed to import LangChain dependencies: {e}")
            raise RuntimeError(
                "LangChain dependencies not installed. "
                "Run: pip install langchain langchain-community langchain-ollama"
            ) from e
