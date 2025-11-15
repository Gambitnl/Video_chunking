"""
Helper functions for resuming processing from intermediate outputs in the UI.
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple

from src.config import Config
from src.intermediate_output import IntermediateOutputManager

logger = logging.getLogger("DDSessionProcessor.intermediate_resume_helper")


def discover_sessions_with_intermediates() -> List[Tuple[str, str]]:
    """
    Discover all sessions with intermediate outputs.

    Returns:
        List of tuples (session_display_name, session_dir_path)
    """
    output_dir = Config.OUTPUT_DIR
    sessions = []

    if not output_dir.exists():
        return sessions

    # Find all session directories
    for session_dir in sorted(output_dir.iterdir(), reverse=True):
        if not session_dir.is_dir():
            continue

        # Skip checkpoint directories
        if session_dir.name.startswith("_"):
            continue

        # Check if intermediates directory exists
        intermediates_dir = session_dir / "intermediates"
        if not intermediates_dir.exists():
            continue

        # Check if any intermediate outputs exist
        manager = IntermediateOutputManager(session_dir)
        has_intermediates = any(
            manager.stage_output_exists(stage) for stage in [4, 5, 6]
        )

        if has_intermediates:
            sessions.append((session_dir.name, str(session_dir)))

    return sessions


def get_available_stages(session_dir: str) -> List[Tuple[int, str]]:
    """
    Get available stages for resuming from a session.

    Args:
        session_dir: Path to the session directory

    Returns:
        List of tuples (stage_number, stage_description)
    """
    session_path = Path(session_dir)
    if not session_path.exists():
        return []

    manager = IntermediateOutputManager(session_path)
    available_stages = []

    stage_descriptions = {
        4: "Stage 4: Merged Transcript → Continue from Diarization",
        5: "Stage 5: Diarization → Continue from Classification",
        6: "Stage 6: Classification → Regenerate Outputs",
    }

    for stage in [4, 5, 6]:
        if manager.stage_output_exists(stage):
            available_stages.append((stage, stage_descriptions[stage]))

    return available_stages


def get_session_info(session_dir: str) -> Dict[str, str]:
    """
    Get information about a session for display.

    Args:
        session_dir: Path to the session directory

    Returns:
        Dictionary with session information
    """
    session_path = Path(session_dir)
    if not session_path.exists():
        return {}

    manager = IntermediateOutputManager(session_path)

    # Get available stages
    available_stages = []
    for stage in [4, 5, 6]:
        if manager.stage_output_exists(stage):
            stage_path = manager.get_stage_path(stage)
            # Get file modification time
            mtime = stage_path.stat().st_mtime
            from datetime import datetime
            timestamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            available_stages.append(f"Stage {stage} (saved {timestamp})")

    return {
        "session_name": session_path.name,
        "session_path": str(session_path),
        "available_stages": ", ".join(available_stages) if available_stages else "None",
        "has_intermediates": len(available_stages) > 0,
    }
