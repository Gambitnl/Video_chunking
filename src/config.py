"""Configuration management"""
import logging
import os
from pathlib import Path
from typing import Optional, Union
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

_logger = logging.getLogger("DDSessionProcessor.config")


class Config:
    """Application configuration"""

    @staticmethod
    def get_env_as_int(key: str, default: int) -> int:
        """Safely get an environment variable as an integer."""
        value = os.getenv(key)
        if value is None or value.strip() == "":
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            _logger.warning(
                "Invalid integer for %s: %r. Using default %s",
                key,
                value,
                default,
            )
            return default

    @staticmethod
    def get_env_as_bool(key: str, default: bool) -> bool:
        """Safely get an environment variable as a boolean."""
        value = os.getenv(key)
        if value is None or value.strip() == "":
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    # API Keys
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    HF_TOKEN: Optional[str] = os.getenv("HF_TOKEN")

    # Model Settings
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "large-v3")
    WHISPER_BACKEND: str = os.getenv("WHISPER_BACKEND", "local")  # local, groq, openai
    LLM_BACKEND: str = os.getenv("LLM_BACKEND", "ollama")  # ollama, openai
    WHISPER_LANGUAGE: str = os.getenv("WHISPER_LANGUAGE", "nl")  # Supported: en, nl
    PYANNOTE_DIARIZATION_MODEL: str = os.getenv(
        "PYANNOTE_DIARIZATION_MODEL",
        "pyannote/speaker-diarization-3.1",
    )
    PYANNOTE_EMBEDDING_MODEL: str = os.getenv(
        "PYANNOTE_EMBEDDING_MODEL",
        "pyannote/embedding",
    )

    # Processing Settings
    CHUNK_LENGTH_SECONDS: int = get_env_as_int("CHUNK_LENGTH_SECONDS", 600)
    CHUNK_OVERLAP_SECONDS: int = get_env_as_int("CHUNK_OVERLAP_SECONDS", 10)
    AUDIO_SAMPLE_RATE: int = get_env_as_int("AUDIO_SAMPLE_RATE", 16000)
    CLEAN_STALE_CLIPS: bool = get_env_as_bool("CLEAN_STALE_CLIPS", True)
    SNIPPET_PLACEHOLDER_MESSAGE: str = os.getenv(
        "SNIPPET_PLACEHOLDER_MESSAGE",
        "No audio snippets were generated for this session."
    )

    # Logging
    LOG_LEVEL_CONSOLE: str = os.getenv("LOG_LEVEL_CONSOLE", "INFO")
    LOG_LEVEL_FILE: str = os.getenv("LOG_LEVEL_FILE", "DEBUG")

    # Ollama Settings
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Paths
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    OUTPUT_DIR: Path = PROJECT_ROOT / "output"
    TEMP_DIR: Path = PROJECT_ROOT / "temp"
    MODELS_DIR: Path = PROJECT_ROOT / "models"

    @classmethod
    def ensure_directories(cls):
        """Ensure all necessary directories exist"""
        cls.OUTPUT_DIR.mkdir(exist_ok=True)
        cls.TEMP_DIR.mkdir(exist_ok=True)
        cls.MODELS_DIR.mkdir(exist_ok=True)

    @classmethod
    def get_inference_device(cls) -> str:
        """
        Resolve the preferred device for model inference.

        Priority:
        1. Explicit INFERENCE_DEVICE environment variable.
        2. CUDA if available.
        3. CPU fallback.
        """
        env_device = os.getenv("INFERENCE_DEVICE")
        if env_device:
            device = env_device.strip().lower()
            if device == "cuda":
                try:
                    import torch  # type: ignore
                    if torch.cuda.is_available():
                        return "cuda"
                except Exception:
                    pass
                _logger.warning(
                    "INFERENCE_DEVICE=cuda requested but CUDA is unavailable. Falling back to cpu."
                )
                return "cpu"
            if device in {"cpu", "cuda"}:
                return device
            _logger.warning(
                "Unknown INFERENCE_DEVICE value '%s'. Falling back to auto-detection.",
                device
            )

        try:
            import torch  # type: ignore
            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"

    @classmethod
    def using_gpu(cls) -> bool:
        """Return True when the preferred inference device resolves to CUDA."""
        return cls.get_inference_device() == "cuda"


# Ensure directories exist on import
Config.ensure_directories()
