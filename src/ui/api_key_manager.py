"""API Key Manager for handling .env file updates."""
from pathlib import Path
from typing import Dict, Optional

from src.config import Config


def load_api_keys() -> Dict[str, str]:
    """Load existing API keys from the .env file."""
    keys = {}
    env_file = Config.PROJECT_ROOT / ".env"
    if not env_file.exists():
        return keys

    lines = env_file.read_text(encoding="utf-8").splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        keys[key.strip()] = value.strip().strip('"')
    return keys


def save_api_keys(
    *,
    groq_api_key: Optional[str] = None,
    hugging_face_api_key: Optional[str] = None
) -> str:
    """Update or create the .env file with new API keys."""
    try:
        env_file = Config.PROJECT_ROOT / ".env"
        if env_file.exists():
            lines = env_file.read_text(encoding="utf-8").splitlines()
        else:
            lines = []

        def _update_or_add_line(key: str, value: Optional[str]) -> bool:
            if value is None:
                return False

            found = False
            for i, line in enumerate(lines):
                if line.strip().startswith(key):
                    lines[i] = f'{key}="{value}"'
                    found = True
                    break
            if not found:
                lines.append(f'{key}="{value}"')
            return True

        updated_groq = _update_or_add_line("GROQ_API_KEY", groq_api_key)
        updated_hf = _update_or_add_line("HUGGING_FACE_API_KEY", hugging_face_api_key)

        if updated_groq or updated_hf or not env_file.exists():
            env_file.write_text("\n".join(lines), encoding="utf-8")

        return "API keys saved successfully."
    except Exception as e:
        return f"Failed to save API keys: {e}"
