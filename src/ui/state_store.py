"""Persist lightweight UI state such as the active campaign selection."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from src.config import Config
from src.file_lock import get_file_lock

logger = logging.getLogger("DDSessionProcessor.ui.state_store")


@dataclass
class UIState:
    """Container for persisted UI preferences."""

    active_campaign_id: Optional[str] = None


class UIStateStore:
    """Manage reading and writing UI state to disk with basic validation."""

    def __init__(self, state_file: Optional[Path] = None) -> None:
        self.state_file = state_file or (Config.TEMP_DIR / "ui_state.json")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> UIState:
        """Return the persisted UI state or an empty default when unavailable."""

        if not self.state_file.exists():
            return UIState()

        try:
            with open(self.state_file, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            logger.warning("Failed to load UI state from %s: %s", self.state_file, exc)
            return UIState()

        return UIState(active_campaign_id=payload.get("active_campaign_id"))

    def load_active_campaign(
        self,
        valid_campaign_ids: Optional[Iterable[str]] = None,
    ) -> Optional[str]:
        """Return the stored active campaign when it is still valid."""

        state = self.load_state()
        if not state.active_campaign_id:
            return None

        if valid_campaign_ids is None:
            return state.active_campaign_id

        valid_ids = set(valid_campaign_ids)
        if state.active_campaign_id in valid_ids:
            return state.active_campaign_id

        logger.info(
            "Discarding persisted campaign '%s' because it is no longer available.",
            state.active_campaign_id,
        )
        self.save_active_campaign(None)
        return None

    def save_state(self, state: UIState) -> None:
        """Persist the provided UI state to disk using a file lock."""

        payload = {"active_campaign_id": state.active_campaign_id}
        try:
            lock = get_file_lock(self.state_file)
            with lock:
                with open(self.state_file, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2, ensure_ascii=False)
        except OSError as exc:
            logger.warning("Failed to persist UI state to %s: %s", self.state_file, exc)

    def save_active_campaign(self, campaign_id: Optional[str]) -> None:
        """Persist only the active campaign selection."""

        self.save_state(UIState(active_campaign_id=campaign_id))
