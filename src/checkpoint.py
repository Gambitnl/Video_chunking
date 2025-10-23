"""Checkpoint management for resumable pipeline processing."""
from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .logger import get_logger


@dataclass
class CheckpointRecord:
    """Serializable checkpoint payload stored on disk."""

    session_id: str
    stage: str
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)
    completed_stages: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        session_id: str,
        stage: str,
        data: Dict[str, Any],
        completed_stages: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "CheckpointRecord":
        return cls(
            session_id=session_id,
            stage=stage,
            timestamp=datetime.utcnow().isoformat(timespec="seconds"),
            data=data,
            completed_stages=list(completed_stages or []),
            metadata=dict(metadata or {}),
        )


class CheckpointManager:
    """Persist and restore pipeline checkpoints for a session."""

    def __init__(self, session_id: str, storage_dir: Path):
        self.session_id = session_id
        self.checkpoint_dir = Path(storage_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(f"checkpoint.{session_id}")

    def _stage_path(self, stage: str) -> Path:
        safe_stage = stage.replace("/", "_")
        return self.checkpoint_dir / f"checkpoint_{safe_stage}.json"

    def save(
        self,
        stage: str,
        data: Dict[str, Any],
        *,
        completed_stages: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Persist checkpoint information for the provided stage."""
        record = CheckpointRecord.create(
            session_id=self.session_id,
            stage=stage,
            data=data,
            completed_stages=completed_stages,
            metadata=metadata,
        )
        path = self._stage_path(stage)
        path.write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")
        self.logger.info("Checkpoint saved for stage '%s' at %s", stage, path)
        return path

    def load(self, stage: str) -> Optional[CheckpointRecord]:
        """Load checkpoint record for a specific stage."""
        path = self._stage_path(stage)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return CheckpointRecord(**data)

    def has_checkpoint(self, stage: str) -> bool:
        """Return True if a checkpoint for the stage exists."""
        return self._stage_path(stage).exists()

    def list_stages(self) -> List[str]:
        """List all stages with saved checkpoints."""
        stages: List[str] = []
        for path in self.checkpoint_dir.glob("checkpoint_*.json"):
            stage = path.stem.replace("checkpoint_", "")
            stages.append(stage)
        return sorted(stages)

    def latest(self) -> Optional[Tuple[str, CheckpointRecord]]:
        """Return the most recent checkpoint (stage, record)."""
        candidates = list(self.checkpoint_dir.glob("checkpoint_*.json"))
        if not candidates:
            return None
        latest_path = max(candidates, key=lambda p: p.stat().st_mtime)
        stage = latest_path.stem.replace("checkpoint_", "")
        record = self.load(stage)
        if record is None:
            return None
        return stage, record

    def clear(self) -> None:
        """Remove all checkpoint files for the session."""
        if self.checkpoint_dir.exists():
            shutil.rmtree(self.checkpoint_dir)
            self.logger.info("Cleared checkpoints for session '%s'", self.session_id)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
