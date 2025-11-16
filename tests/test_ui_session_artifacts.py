"""Tests for the Session Artifact Explorer UI."""
from pathlib import Path
from typing import List
from unittest.mock import patch

import gradio as gr
import pandas as pd
import pytest

from src.ui.session_artifacts_tab import (
    create_session_artifacts_tab,
    download_session_zip,
    go_up_directory,
    handle_artifact_selection,
    on_session_selected,
    refresh_sessions,
)


def test_create_session_artifacts_tab():
    """Ensure the Artifact Explorer tab renders the expected components."""
    with gr.Blocks() as demo:
        refs = create_session_artifacts_tab(demo)

    assert isinstance(refs, dict)
    assert "session_picker" in refs
    assert "file_list" in refs
    assert "session_zip_file" in refs


def test_refresh_sessions_success(monkeypatch):
    """Dropdown should be populated when the API returns sessions."""
    monkeypatch.setattr(
        "src.ui.session_artifacts_tab.list_sessions_api",
        lambda: {
            "status": "success",
            "data": {
                "sessions": [
                    {"relative_path": "20251116_120000_session_a"},
                    {"relative_path": "20251115_100000_session_b"},
                ]
            },
            "error": None,
        },
    )

    dropdown_update, status_markdown = refresh_sessions()
    assert dropdown_update["choices"] == [
        "20251116_120000_session_a",
        "20251115_100000_session_b",
    ]
    assert "Select a session" in status_markdown


def test_refresh_sessions_error(monkeypatch):
    """Refresh should handle API errors gracefully."""
    monkeypatch.setattr(
        "src.ui.session_artifacts_tab.list_sessions_api",
        lambda: {"status": "error", "data": None, "error": "boom"},
    )

    dropdown_update, status_markdown = refresh_sessions()
    assert dropdown_update["choices"] == []
    assert "boom" in status_markdown


def test_on_session_selected_success(monkeypatch):
    """Selecting a session should list its artifacts."""
    monkeypatch.setattr(
        "src.ui.session_artifacts_tab.get_directory_tree_api",
        lambda rel: {
            "status": "success",
            "data": {
                "items": [
                    {
                        "name": "notes.txt",
                        "relative_path": f"{rel}/notes.txt",
                        "artifact_type": ".txt",
                        "size_bytes": 128,
                        "created": "2025-11-16T12:00:00",
                        "modified": "2025-11-16T12:00:00",
                        "is_directory": False,
                    }
                ]
            },
            "error": None,
        },
    )

    outputs = on_session_selected("20251116_120000_session_a")
    dataframe_update = outputs[0]
    session_state = outputs[-1]
    assert isinstance(dataframe_update["value"], pd.DataFrame)
    assert "notes.txt" in dataframe_update["value"]["Name"].values
    assert session_state == "20251116_120000_session_a"


def test_on_session_selected_failure(monkeypatch):
    """Session selection should emit an error when API fails."""
    monkeypatch.setattr(
        "src.ui.session_artifacts_tab.get_directory_tree_api",
        lambda rel: {"status": "error", "data": None, "error": "missing"},
    )

    outputs = on_session_selected("invalid_session")
    status_markdown = outputs[1]
    assert "missing" in status_markdown


def test_handle_artifact_selection_directory(monkeypatch):
    """Selecting a directory should navigate into it."""
    child_path = "session/intermediates"

    def mock_tree(path):
        return {
            "status": "success",
            "data": {
                "items": [
                    {
                        "name": "child.txt",
                        "relative_path": f"{path}/child.txt",
                        "artifact_type": ".txt",
                        "size_bytes": 20,
                        "created": "2025-11-16T12:00:00",
                        "modified": "2025-11-16T12:00:00",
                        "is_directory": False,
                    }
                ]
            },
            "error": None,
        }

    monkeypatch.setattr("src.ui.session_artifacts_tab.get_directory_tree_api", mock_tree)
    items = [
        {
            "name": "intermediates",
            "relative_path": child_path,
            "artifact_type": "directory",
            "size_bytes": 0,
            "created": "2025-11-16T12:00:00",
            "modified": "2025-11-16T12:00:00",
            "is_directory": True,
        }
    ]
    evt = type("Evt", (), {"index": (0, 0)})()

    outputs = handle_artifact_selection(items, "session", evt)
    status_markdown = outputs[1]
    new_path_box = outputs[7]
    assert "intermediates" in status_markdown
    assert new_path_box["value"] == child_path


def test_handle_artifact_selection_file(monkeypatch, tmp_path):
    """Selecting a file should show preview and download link."""
    file_path = tmp_path / "session" / "notes.txt"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("hello world")

    monkeypatch.setattr(
        "src.ui.session_artifacts_tab.get_file_preview_api",
        lambda rel, max_size_kb=10, encoding="utf-8": {
            "status": "success",
            "data": {
                "relative_path": rel,
                "content": "hello world",
                "truncated": False,
                "encoding": "utf-8",
                "byte_length": 11,
            },
            "error": None,
        },
    )
    monkeypatch.setattr(
        "src.ui.session_artifacts_tab.download_file_api",
        lambda rel: (file_path, Path(rel).name),
    )

    items: List[Dict[str, str]] = [
        {
            "name": "notes.txt",
            "relative_path": "session/notes.txt",
            "artifact_type": ".txt",
            "size_bytes": 11,
            "created": "2025-11-16T12:00:00",
            "modified": "2025-11-16T12:00:00",
            "is_directory": False,
        }
    ]
    evt = type("Evt", (), {"index": (0, 0)})()

    outputs = handle_artifact_selection(items, "session", evt)
    preview_box = outputs[2]
    file_component = outputs[3]
    assert preview_box["value"] == "hello world"
    assert file_component["visible"] is True
    assert file_component["value"] == str(file_path)


def test_go_up_directory_root(monkeypatch):
    """Attempting to navigate above the root should emit an info message."""
    outputs = go_up_directory("session", "session", [])
    status_markdown = outputs[1]
    assert "Already viewing" in status_markdown


def test_download_session_zip(monkeypatch, tmp_path):
    """The session zip helper should surface download paths."""
    zip_path = tmp_path / "session.zip"
    zip_path.write_text("zip")
    monkeypatch.setattr(
        "src.ui.session_artifacts_tab.download_session_api",
        lambda rel: (zip_path, zip_path.name),
    )

    file_update, status_markdown = download_session_zip("session")
    assert file_update["visible"] is True
    assert file_update["value"] == str(zip_path)
    assert "Session archive ready" in status_markdown
