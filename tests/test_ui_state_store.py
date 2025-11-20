"""Tests for the UIStateStore helper."""

from pathlib import Path

import json

import pytest

from src.file_lock import clear_lock_registry
from src.ui.state_store import UIStateStore


@pytest.fixture(autouse=True)
def reset_file_locks():
    """Ensure each test runs with a clean lock registry."""

    clear_lock_registry()
    yield
    clear_lock_registry()


def test_load_active_campaign_returns_none_when_file_missing(tmp_path: Path):
    store = UIStateStore(state_file=tmp_path / "ui_state.json")

    assert store.load_active_campaign() is None


def test_save_and_load_active_campaign_round_trip(tmp_path: Path):
    state_path = tmp_path / "ui_state.json"
    store = UIStateStore(state_file=state_path)

    store.save_active_campaign("campaign_001")

    reloaded = UIStateStore(state_file=state_path)

    assert reloaded.load_active_campaign({"campaign_001"}) == "campaign_001"


def test_load_active_campaign_handles_invalid_json(tmp_path: Path):
    state_path = tmp_path / "ui_state.json"
    state_path.write_text("not json", encoding="utf-8")

    store = UIStateStore(state_file=state_path)

    assert store.load_active_campaign() is None


def test_load_active_campaign_discards_missing_id(tmp_path: Path):
    state_path = tmp_path / "ui_state.json"
    with open(state_path, "w", encoding="utf-8") as handle:
        json.dump({"active_campaign_id": "campaign_999"}, handle)

    store = UIStateStore(state_file=state_path)

    assert store.load_active_campaign({"campaign_001"}) is None
    assert json.loads(state_path.read_text(encoding="utf-8"))["active_campaign_id"] is None
