"""Configuration management"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration"""

    # API Keys
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    # Model Settings
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "large-v3")
    WHISPER_BACKEND: str = os.getenv("WHISPER_BACKEND", "local")  # local, groq, openai
    LLM_BACKEND: str = os.getenv("LLM_BACKEND", "ollama")  # ollama, openai

    # Processing Settings
    CHUNK_LENGTH_SECONDS: int = int(os.getenv("CHUNK_LENGTH_SECONDS", "600"))
    CHUNK_OVERLAP_SECONDS: int = int(os.getenv("CHUNK_OVERLAP_SECONDS", "10"))
    AUDIO_SAMPLE_RATE: int = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))

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


# Ensure directories exist on import
Config.ensure_directories()
