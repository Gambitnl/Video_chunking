"""Central status tracking for session processing."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import Config

STATUS_FILE = Config.PROJECT_ROOT / "logs" / "session_status.json"

STAGES = [
    {"id": 1, "name": "Audio Conversion"},
    {"id": 2, "name": "Chunking"},
    {"id": 3, "name": "Transcription"},
    {"id": 4, "name": "Merge Overlaps"},
    {"id": 5, "name": "Speaker Diarization"},
    {"id": 6, "name": "IC/OOC Classification"},
    {"id": 7, "name": "Output Generation"},
    {"id": 8, "name": "Audio Snippet Export"},
]


def _timestamp() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        clean = value[:-1] if value.endswith("Z") else value
        return datetime.fromisoformat(clean)
    except ValueError:
        return None


def _duration_seconds(start: Optional[str], end: Optional[str]) -> Optional[float]:
    start_dt = _parse_timestamp(start)
    end_dt = _parse_timestamp(end)
    if not start_dt or not end_dt:
        return None
    return round((end_dt - start_dt).total_seconds(), 2)


def _sanitize(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize(v) for v in value]
    return str(value)


def _append_event(data: Dict, stage_id: int, event_type: str, message: str = "") -> None:
    default_name = "Session" if stage_id == 0 else f"Stage {stage_id}"
    stage_name = next((s["name"] for s in STAGES if s["id"] == stage_id), default_name)
    events: List[Dict[str, Any]] = data.setdefault("events", [])  # type: ignore[assignment]
    events.append(
        {
            "timestamp": _timestamp(),
            "stage_id": stage_id,
            "stage_name": stage_name,
            "event": event_type,
            "message": message,
        }
    )
    if len(events) > 200:
        del events[: len(events) - 200]




def _next_stage_name(current_stage_id: int, stages: List[Dict[str, Any]]) -> Optional[str]:
    for stage_meta in STAGES:
        if stage_meta["id"] <= current_stage_id:
            continue
        for stage in stages:
            if stage.get("id") == stage_meta["id"]:
                if stage.get("state") not in {"skipped", "completed"}:
                    return stage_meta["name"]
                break
    return None
class StatusTracker:
    """Persist session status for monitoring UIs."""

    @classmethod
    def _read(cls) -> Optional[Dict]:
        if not STATUS_FILE.exists():
            return None
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None

    @classmethod
    def _write(cls, data: Dict) -> None:
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data["updated_at"] = _timestamp()
        STATUS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def start_session(
        cls,
        session_id: str,
        skip_flags: Dict[str, bool],
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        sanitized_options = _sanitize(options or {})
        started_at = _timestamp()

        stages_state: List[Dict[str, Any]] = []
        for stage in STAGES:
            state = "pending"
            message = ""
            if stage["id"] == 5 and skip_flags.get("diarization"):
                state = "skipped"
                message = "Speaker diarization skipped by user"
            if stage["id"] == 6 and skip_flags.get("classification"):
                state = "skipped"
                message = "IC/OOC classification skipped by user"
            if stage["id"] == 8 and skip_flags.get("snippets"):
                state = "skipped"
                message = "Audio snippet export skipped by user"

            stages_state.append(
                {
                    "id": stage["id"],
                    "name": stage["name"],
                    "state": state,
                    "message": message,
                    "started_at": None,
                    "ended_at": None,
                    "duration_seconds": None,
                }
            )

        data = {
            "session_id": session_id,
            "processing": True,
            "status": "running",
            "current_stage": None,
            "skip_flags": skip_flags,
            "options": sanitized_options,
            "stages": stages_state,
            "events": [],
            "started_at": started_at,
            "completed_at": None,
        }

        summary_bits = []
        if sanitized_options.get("using_party_config"):
            summary_bits.append(f"party={sanitized_options.get('party_id') or 'default'}")
        else:
            summary_bits.append('party=manual')
        speakers = sanitized_options.get("num_speakers")
        if speakers is not None:
            summary_bits.append(f'num_speakers={speakers}')
        for flag_key in ("skip_diarization", "skip_classification", "skip_snippets"):
            if flag_key in sanitized_options:
                flag_value = 'yes' if sanitized_options.get(flag_key) else 'no'
                summary_bits.append(f"{flag_key}={flag_value}")
        summary = ", ".join(summary_bits) if summary_bits else ""
        _append_event(data, 0, 'session_started', summary)

        cls._write(data)

    @classmethod
    def update_stage(
        cls,
        session_id: str,
        stage_id: int,
        state: str,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        data = cls._read()
        if not data or data.get("session_id") != session_id:
            return

        stages = data.get("stages", [])
        stage_entry: Optional[Dict[str, Any]] = None
        for stage in stages:
            if stage["id"] == stage_id:
                stage_entry = stage
                break

        if stage_entry is None:
            return

        now = _timestamp()

        stage_entry["state"] = state
        if message:
            stage_entry["message"] = message
        if details:
            stage_entry["details"] = _sanitize(details)

        event_message = message

        if state == "running":
            if not stage_entry.get("started_at"):
                stage_entry["started_at"] = now
            stage_entry["ended_at"] = None
            stage_entry["duration_seconds"] = None
            data["current_stage"] = stage_id
            if not event_message:
                event_message = "Stage started"
            _append_event(data, stage_id, "started", event_message)
        else:
            if not stage_entry.get("started_at"):
                stage_entry["started_at"] = now
            stage_entry["ended_at"] = now
            stage_entry["duration_seconds"] = _duration_seconds(
                stage_entry.get("started_at"), now
            )
            if state in {"completed", "skipped"}:
                data["current_stage"] = None
                next_stage = _next_stage_name(stage_id, stages)
                if next_stage:
                    suffix = f" | Next: {next_stage}"
                    event_message = f"{event_message}{suffix}" if event_message else f"Next: {next_stage}"
            elif state == "failed":
                data["current_stage"] = None
            if not event_message:
                event_message = state.capitalize()
            if state in {"completed", "skipped", "failed"}:
                _append_event(data, stage_id, state, event_message)
            else:
                _append_event(data, stage_id, "updated", event_message)

        cls._write(data)

    @classmethod
    def complete_session(cls, session_id: str) -> None:
        data = cls._read()
        if not data or data.get("session_id") != session_id:
            return
        now = _timestamp()
        data["processing"] = False
        data["status"] = "completed"
        data["current_stage"] = None
        data["completed_at"] = now
        data["duration_seconds"] = _duration_seconds(data.get("started_at"), now)
        _append_event(data, 0, "session_completed", "Session completed successfully")
        cls._write(data)

    @classmethod
    def fail_session(cls, session_id: str, error: str) -> None:
        data = cls._read()
        if not data or data.get("session_id") != session_id:
            return
        now = _timestamp()
        data["processing"] = False
        data["status"] = "failed"
        data["error"] = error
        data["current_stage"] = None
        data["completed_at"] = now
        data["duration_seconds"] = _duration_seconds(data.get("started_at"), now)
        _append_event(data, 0, "session_failed", error)
        cls._write(data)

    @classmethod
    def get_snapshot(cls) -> Optional[Dict]:
        return cls._read()
