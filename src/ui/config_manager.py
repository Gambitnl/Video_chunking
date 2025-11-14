"""Configuration Manager for handling .env file updates with validation."""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.config import Config

logger = logging.getLogger("DDSessionProcessor.config_manager")


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigManager:
    """Manages configuration persistence and validation."""

    # Define valid choices for configuration options
    VALID_WHISPER_BACKENDS = ["local", "groq", "openai"]
    VALID_DIARIZATION_BACKENDS = ["local", "huggingface"]
    VALID_LLM_BACKENDS = ["ollama", "openai", "groq", "colab"]
    VALID_WHISPER_LANGUAGES = ["en", "nl"]
    VALID_WHISPER_MODELS = [
        "tiny", "base", "small", "medium", "large",
        "large-v2", "large-v3", "large-v3-turbo"
    ]

    @staticmethod
    def load_env_config() -> Dict[str, str]:
        """Load existing configuration from the .env file."""
        config = {}
        env_file = Config.PROJECT_ROOT / ".env"
        if not env_file.exists():
            return config

        lines = env_file.read_text(encoding="utf-8").splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            config[key.strip()] = value.strip().strip('"')
        return config

    @staticmethod
    def _validate_positive_int(value: Any, name: str) -> int:
        """Validate that a value is a positive integer."""
        try:
            int_val = int(value)
            if int_val <= 0:
                raise ConfigValidationError(f"{name} must be a positive integer, got {value}")
            return int_val
        except (ValueError, TypeError):
            raise ConfigValidationError(f"{name} must be a valid integer, got {value}")

    @staticmethod
    def _validate_non_negative_int(value: Any, name: str) -> int:
        """Validate that a value is a non-negative integer."""
        try:
            int_val = int(value)
            if int_val < 0:
                raise ConfigValidationError(f"{name} must be non-negative, got {value}")
            return int_val
        except (ValueError, TypeError):
            raise ConfigValidationError(f"{name} must be a valid integer, got {value}")

    @staticmethod
    def _validate_positive_float(value: Any, name: str) -> float:
        """Validate that a value is a positive float."""
        try:
            float_val = float(value)
            if float_val <= 0:
                raise ConfigValidationError(f"{name} must be a positive number, got {value}")
            return float_val
        except (ValueError, TypeError):
            raise ConfigValidationError(f"{name} must be a valid number, got {value}")

    @staticmethod
    def _validate_choice(value: str, choices: List[str], name: str) -> str:
        """Validate that a value is in the allowed choices."""
        if value not in choices:
            raise ConfigValidationError(
                f"{name} must be one of {choices}, got '{value}'"
            )
        return value

    @staticmethod
    def _validate_url(value: str, name: str) -> str:
        """Basic URL validation."""
        value = value.strip()
        if not value:
            raise ConfigValidationError(f"{name} cannot be empty")
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ConfigValidationError(f"{name} must start with http:// or https://")
        return value

    @classmethod
    def validate_config(
        cls,
        *,
        # API Keys
        groq_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        hugging_face_api_key: Optional[str] = None,
        # Model Settings
        whisper_model: Optional[str] = None,
        whisper_backend: Optional[str] = None,
        diarization_backend: Optional[str] = None,
        llm_backend: Optional[str] = None,
        whisper_language: Optional[str] = None,
        ollama_model: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
        ollama_fallback_model: Optional[str] = None,
        # Processing Settings
        chunk_length_seconds: Optional[Any] = None,
        chunk_overlap_seconds: Optional[Any] = None,
        audio_sample_rate: Optional[Any] = None,
        clean_stale_clips: Optional[bool] = None,
        # Rate Limiting
        groq_max_calls_per_second: Optional[Any] = None,
        groq_rate_limit_period_seconds: Optional[Any] = None,
        groq_rate_limit_burst: Optional[Any] = None,
        # Colab Settings
        colab_poll_interval: Optional[Any] = None,
        colab_timeout: Optional[Any] = None,
    ) -> Tuple[Dict[str, str], List[str]]:
        """
        Validate configuration values.

        Returns:
            Tuple of (validated_config_dict, validation_errors_list)
        """
        validated = {}
        errors = []

        try:
            # Validate Model Settings
            if whisper_backend is not None:
                validated["WHISPER_BACKEND"] = cls._validate_choice(
                    whisper_backend, cls.VALID_WHISPER_BACKENDS, "Whisper Backend"
                )

            if diarization_backend is not None:
                validated["DIARIZATION_BACKEND"] = cls._validate_choice(
                    diarization_backend, cls.VALID_DIARIZATION_BACKENDS, "Diarization Backend"
                )

            if llm_backend is not None:
                validated["LLM_BACKEND"] = cls._validate_choice(
                    llm_backend, cls.VALID_LLM_BACKENDS, "LLM Backend"
                )

            if whisper_language is not None:
                validated["WHISPER_LANGUAGE"] = cls._validate_choice(
                    whisper_language, cls.VALID_WHISPER_LANGUAGES, "Whisper Language"
                )

            if whisper_model is not None:
                validated["WHISPER_MODEL"] = cls._validate_choice(
                    whisper_model, cls.VALID_WHISPER_MODELS, "Whisper Model"
                )

            # Validate Processing Settings
            if chunk_length_seconds is not None:
                validated["CHUNK_LENGTH_SECONDS"] = str(
                    cls._validate_positive_int(chunk_length_seconds, "Chunk Length")
                )

            if chunk_overlap_seconds is not None:
                validated["CHUNK_OVERLAP_SECONDS"] = str(
                    cls._validate_non_negative_int(chunk_overlap_seconds, "Chunk Overlap")
                )

            if audio_sample_rate is not None:
                validated["AUDIO_SAMPLE_RATE"] = str(
                    cls._validate_positive_int(audio_sample_rate, "Audio Sample Rate")
                )

            if clean_stale_clips is not None:
                validated["CLEAN_STALE_CLIPS"] = "true" if clean_stale_clips else "false"

            # Validate Ollama Settings
            if ollama_model is not None and ollama_model.strip():
                validated["OLLAMA_MODEL"] = ollama_model.strip()

            if ollama_base_url is not None and ollama_base_url.strip():
                validated["OLLAMA_BASE_URL"] = cls._validate_url(
                    ollama_base_url, "Ollama Base URL"
                )

            if ollama_fallback_model is not None:
                # Empty string is valid (means no fallback)
                validated["OLLAMA_FALLBACK_MODEL"] = ollama_fallback_model.strip()

            # Validate Rate Limiting Settings
            if groq_max_calls_per_second is not None:
                validated["GROQ_MAX_CALLS_PER_SECOND"] = str(
                    cls._validate_positive_int(groq_max_calls_per_second, "Groq Max Calls Per Second")
                )

            if groq_rate_limit_period_seconds is not None:
                validated["GROQ_RATE_LIMIT_PERIOD_SECONDS"] = str(
                    cls._validate_positive_float(groq_rate_limit_period_seconds, "Groq Rate Limit Period")
                )

            if groq_rate_limit_burst is not None:
                validated["GROQ_RATE_LIMIT_BURST"] = str(
                    cls._validate_positive_int(groq_rate_limit_burst, "Groq Rate Limit Burst")
                )

            # Validate Colab Settings
            if colab_poll_interval is not None:
                validated["COLAB_POLL_INTERVAL"] = str(
                    cls._validate_positive_int(colab_poll_interval, "Colab Poll Interval")
                )

            if colab_timeout is not None:
                validated["COLAB_TIMEOUT"] = str(
                    cls._validate_positive_int(colab_timeout, "Colab Timeout")
                )

            # API Keys (no validation, just store if provided)
            if groq_api_key is not None and groq_api_key.strip():
                validated["GROQ_API_KEY"] = groq_api_key.strip()

            if openai_api_key is not None and openai_api_key.strip():
                validated["OPENAI_API_KEY"] = openai_api_key.strip()

            if hugging_face_api_key is not None and hugging_face_api_key.strip():
                validated["HUGGING_FACE_API_KEY"] = hugging_face_api_key.strip()

        except ConfigValidationError as e:
            errors.append(str(e))

        return validated, errors

    @staticmethod
    def save_config(config_updates: Dict[str, str]) -> None:
        """
        Update or create the .env file with new configuration values.

        Args:
            config_updates: Dictionary of key-value pairs to update in .env file
        """
        env_file = Config.PROJECT_ROOT / ".env"
        if env_file.exists():
            lines = env_file.read_text(encoding="utf-8").splitlines()
        else:
            lines = []

        updated_keys = set()

        # Update existing lines
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith("#") or "=" not in line_stripped:
                continue

            key = line_stripped.split("=", 1)[0].strip()
            if key in config_updates:
                lines[i] = f'{key}="{config_updates[key]}"'
                updated_keys.add(key)

        # Add new lines for keys that weren't found
        for key, value in config_updates.items():
            if key not in updated_keys:
                lines.append(f'{key}="{value}"')

        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger.info("Configuration saved to .env file: %s", list(config_updates.keys()))
