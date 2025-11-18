"""Helper functions for System Diagnostics and Conversation Management."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from src.config import Config
from src.ui.helpers import StatusMessages


def run_health_check() -> str:
    """
    Run system health check to verify dependencies and configuration.

    Returns:
        Markdown-formatted health check results
    """
    checks = []

    # Check FFmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True, timeout=5)
        checks.append(("FFmpeg", True, "Installed"))
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        checks.append(("FFmpeg", False, "Not found - please install from https://ffmpeg.org"))

    # Check PyTorch
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            checks.append(("PyTorch", True, "Installed with CUDA"))
        else:
            checks.append(("PyTorch", True, "Installed (CPU only)"))
    except ImportError:
        checks.append(("PyTorch", False, "Not installed"))

    # Check faster-whisper
    try:
        import faster_whisper
        checks.append(("faster-whisper", True, "Installed"))
    except ImportError:
        checks.append(("faster-whisper", False, "Not installed"))

    # Check pyannote.audio
    try:
        import pyannote.audio
        checks.append(("pyannote.audio", True, "Installed"))
    except ImportError:
        checks.append(("pyannote.audio", False, "Not installed"))

    # Check Ollama connection
    try:
        import ollama
        client = ollama.Client(host=Config.OLLAMA_BASE_URL)
        client.list()
        checks.append(("Ollama", True, f"Running at {Config.OLLAMA_BASE_URL}"))
    except Exception as e:
        error_msg = str(e)[:50]
        checks.append(("Ollama", False, f"Not running - {error_msg}"))

    # Check Groq API (if configured)
    if Config.GROQ_API_KEY:
        checks.append(("Groq API Key", True, "Configured"))
    else:
        checks.append(("Groq API Key", False, "Not configured"))

    # Check OpenAI API (if configured)
    if Config.OPENAI_API_KEY:
        checks.append(("OpenAI API Key", True, "Configured"))
    else:
        checks.append(("OpenAI API Key", False, "Not configured"))

    # Check HuggingFace Token (if configured)
    if Config.HF_TOKEN:
        checks.append(("HuggingFace Token", True, "Configured"))
    else:
        checks.append(("HuggingFace Token", False, "Not configured"))

    # Build markdown output
    all_ok = all(check[1] for check in checks)

    if all_ok:
        header = StatusMessages.success(
            "System Health Check",
            "All dependencies are ready!"
        )
    else:
        header = StatusMessages.warning(
            "System Health Check",
            "Some dependencies are missing or not configured."
        )

    # Build table
    table_rows = []
    table_rows.append("| Component | Status | Details |")
    table_rows.append("|-----------|--------|---------|")

    for name, success, details in checks:
        status = "✓" if success else "✗"
        table_rows.append(f"| {name} | {status} | {details} |")

    table = "\n".join(table_rows)

    result = f"{header}\n\n{table}"

    if not all_ok:
        result += "\n\n**Note**: Run `pip install -r requirements.txt` to install missing dependencies."

    return result


def export_diagnostics() -> Tuple[str, str]:
    """
    Export system diagnostics to JSON and markdown.

    Returns:
        Tuple of (markdown_message, json_data)
    """
    # Gather system info
    diagnostics = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "whisper_backend": Config.WHISPER_BACKEND,
            "whisper_model": Config.WHISPER_MODEL,
            "whisper_language": Config.WHISPER_LANGUAGE,
            "diarization_backend": Config.DIARIZATION_BACKEND,
            "llm_backend": Config.LLM_BACKEND,
            "ollama_model": Config.OLLAMA_MODEL,
            "ollama_base_url": Config.OLLAMA_BASE_URL,
            "chunk_length_seconds": Config.CHUNK_LENGTH_SECONDS,
            "chunk_overlap_seconds": Config.CHUNK_OVERLAP_SECONDS,
            "audio_sample_rate": Config.AUDIO_SAMPLE_RATE,
        },
        "api_keys_configured": {
            "groq": bool(Config.GROQ_API_KEY),
            "openai": bool(Config.OPENAI_API_KEY),
            "huggingface": bool(Config.HF_TOKEN),
        },
    }

    # Save to file
    output_dir = Path("output/diagnostics")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"diagnostics_{timestamp}.json"

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(diagnostics, f, indent=2)

    message = StatusMessages.success(
        "Diagnostics Exported",
        f"System diagnostics saved to: {json_path}"
    )

    return message, json.dumps(diagnostics, indent=2)


def list_conversations() -> str:
    """
    List all saved conversations.

    Returns:
        Markdown-formatted list of conversations
    """
    try:
        from src.langchain.conversation_store import ConversationStore

        conversations_dir = Path("models/conversations")
        if not conversations_dir.exists():
            return StatusMessages.info(
                "Conversations",
                "No conversations directory found. Start a campaign chat to create conversations."
            )

        store = ConversationStore(conversations_dir)
        conversations = store.list_conversations(limit=100)

        if not conversations:
            return StatusMessages.info(
                "Conversations",
                "No saved conversations found."
            )

        # Build markdown table
        header = StatusMessages.info(
            "Saved Conversations",
            f"Found {len(conversations)} conversation(s)."
        )

        table_rows = []
        table_rows.append("| ID | Campaign | Messages | Created | Updated |")
        table_rows.append("|---------|----------|----------|---------|---------|")

        for conv in conversations:
            conv_id = conv.get('conversation_id', 'unknown')
            campaign = conv.get('context', {}).get('campaign', 'N/A')
            msg_count = len(conv.get('messages', []))
            created = conv.get('created_at', 'unknown')[:19]  # Truncate to datetime
            updated = conv.get('updated_at', 'unknown')[:19]  # Truncate to datetime

            table_rows.append(f"| `{conv_id}` | {campaign} | {msg_count} | {created} | {updated} |")

        table = "\n".join(table_rows)

        return f"{header}\n\n{table}"

    except ImportError:
        return StatusMessages.error(
            "LangChain Not Available",
            "LangChain features are not installed. Conversation management requires LangChain."
        )
    except Exception as e:
        return StatusMessages.error(
            "Error Listing Conversations",
            f"Failed to list conversations: {str(e)}"
        )


def clear_all_conversations() -> str:
    """
    Clear all saved conversations.

    Returns:
        Markdown-formatted confirmation message
    """
    try:
        conversations_dir = Path("models/conversations")
        if not conversations_dir.exists():
            return StatusMessages.info(
                "Conversations",
                "No conversations directory found. Nothing to clear."
            )

        # Count conversations before deletion
        conversation_files = list(conversations_dir.glob("conv_*.json"))
        count = len(conversation_files)

        if count == 0:
            return StatusMessages.info(
                "Conversations",
                "No conversations found to clear."
            )

        # Delete all conversation files
        for conv_file in conversation_files:
            try:
                conv_file.unlink()
            except Exception as e:
                return StatusMessages.error(
                    "Error Deleting Conversation",
                    f"Failed to delete {conv_file.name}: {str(e)}"
                )

        return StatusMessages.success(
            "Conversations Cleared",
            f"Successfully deleted {count} conversation(s)."
        )

    except Exception as e:
        return StatusMessages.error(
            "Error Clearing Conversations",
            f"Failed to clear conversations: {str(e)}"
        )
