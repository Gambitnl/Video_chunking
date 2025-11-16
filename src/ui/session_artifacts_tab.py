"""UI components for the Session Artifact Explorer tab."""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
import pandas as pd

from src.api.session_artifacts import (
    download_file_api,
    download_session_api,
    get_directory_tree_api,
    get_file_preview_api,
    list_sessions_api,
)
from src.ui.helpers import StatusMessages

COLUMNS = [
    "Name",
    "Type",
    "Size (Bytes)",
    "Created",
    "Modified",
    "Path",
    "Directory",
]


def _empty_dataframe() -> pd.DataFrame:
    """Return an empty dataframe with the expected columns."""
    return pd.DataFrame(columns=COLUMNS)


def _format_timestamp(value: str) -> str:
    """Format ISO timestamp strings for display."""
    if not value:
        return ""
    try:
        # Handle naive + timezone-aware values
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(value)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return value


def _build_table(items: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert API artifacts into a dataframe for the UI."""
    rows = []
    for item in items:
        rows.append({
            "Name": item["name"],
            "Type": item["artifact_type"],
            "Size (Bytes)": item["size_bytes"],
            "Created": _format_timestamp(item["created"]),
            "Modified": _format_timestamp(item["modified"]),
            "Path": item["relative_path"],
            "Directory": "Yes" if item["is_directory"] else "No",
        })
    if not rows:
        return _empty_dataframe()
    return pd.DataFrame(rows, columns=COLUMNS)


def refresh_sessions():
    """Load the list of sessions via the SessionArtifactsAPI."""
    response = list_sessions_api()
    if response["status"] != "success":
        return (
            gr.update(choices=[], value=None),
            StatusMessages.error("Error", response["error"] or "Failed to load sessions."),
        )

    sessions = response["data"]["sessions"]
    choices = [session["relative_path"] for session in sessions]
    message = (
        StatusMessages.info(
            "Ready",
            f"Select a session to explore ({len(sessions)} available)."
        )
        if sessions
        else StatusMessages.info("Ready", "No processed sessions were found.")
    )
    return gr.update(choices=choices, value=None), message


def _directory_error(message: str):
    """Return a standard set of updates when directory interaction fails."""
    return (
        gr.update(value=_empty_dataframe()),
        StatusMessages.error("Error", message),
        gr.update(value="", placeholder="Select a file to preview its content."),
        gr.update(value=None, visible=False),
        None,
        None,
        [],
        gr.update(value=""),
        gr.update(value=None, visible=False),
    )


def _directory_success(relative_path: str, items: List[Dict[str, Any]]):
    """Return updates for a successful directory listing."""
    df = _build_table(items)
    return (
        gr.update(value=df),
        StatusMessages.success("Success", f"Showing {len(items)} items in {relative_path}."),
        gr.update(value="", placeholder="Select a file to preview its content."),
        gr.update(value=None, visible=False),
        None,
        relative_path,
        items,
        gr.update(value=relative_path),
        gr.update(value=None, visible=False),
    )


def _load_directory(relative_path: Optional[str]):
    """Fetch directory contents for the provided path."""
    if not relative_path:
        return _directory_error("Select a session to begin.")

    response = get_directory_tree_api(relative_path)
    if response["status"] != "success":
        return _directory_error(response["error"] or "Failed to load directory.")

    items = response["data"]["items"]
    return _directory_success(relative_path, items)


def on_session_selected(session_path: Optional[str]):
    """Handle a new session selection."""
    directory_outputs = _load_directory(session_path)
    return (*directory_outputs, session_path)


def handle_directory_navigation(target_path: Optional[str]):
    """Navigate to a given directory path."""
    return _load_directory(target_path)


def go_up_directory(
    current_path: Optional[str],
    session_root: Optional[str],
    current_items: Optional[List[Dict[str, Any]]] = None,
):
    """Navigate to the parent directory."""
    if not current_path or not session_root:
        return _directory_error("Select a session to begin.")

    if current_path == session_root:
        return (
            gr.update(),
            StatusMessages.info("Ready", "Already viewing the session root."),
            gr.update(),
            gr.update(),
            None,
            current_path,
            current_items or [],
            gr.update(),
            gr.update(value=None, visible=False),
        )

    parent = str(Path(current_path).parent)
    if parent == ".":
        parent = session_root
    return _load_directory(parent)


def handle_artifact_selection(
    items: List[Dict[str, Any]],
    current_directory: Optional[str],
    evt: gr.SelectData,
):
    """Respond to row selection within the artifacts table."""
    if not items or evt is None or evt.index is None:
        return (
            gr.update(),
            StatusMessages.info("Ready", "Select a session to begin."),
            gr.update(),
            gr.update(),
            None,
            current_directory,
            items,
            gr.update(),
            gr.update(value=None, visible=False),
        )

    row_index = evt.index[0]
    if row_index is None or row_index >= len(items):
        return _directory_error("Invalid selection index received.")

    selected = items[row_index]
    if selected["is_directory"]:
        return _load_directory(selected["relative_path"])

    preview_response = get_file_preview_api(selected["relative_path"])
    if preview_response["status"] != "success":
        return (
            gr.update(),
            StatusMessages.error("Error", preview_response["error"] or "Failed to preview file."),
            gr.update(value="", placeholder="Select a file to preview its content."),
            gr.update(value=None, visible=False),
            None,
            current_directory,
            items,
            gr.update(),
            gr.update(value=None, visible=False),
        )

    preview_data = preview_response["data"]
    preview_text = preview_data["content"]
    if preview_data.get("truncated"):
        preview_text += "\n\n[Preview truncated]"

    download_tuple = download_file_api(selected["relative_path"])
    if not download_tuple:
        return (
            gr.update(),
            StatusMessages.error("Error", "Unable to prepare file for download."),
            gr.update(value=preview_text),
            gr.update(value=None, visible=False),
            None,
            current_directory,
            items,
            gr.update(),
            gr.update(value=None, visible=False),
        )

    file_path, _filename = download_tuple
    return (
        gr.update(),
        StatusMessages.success("Success", f"Previewing {selected['name']}."),
        gr.update(value=preview_text),
        gr.update(value=str(file_path), visible=True),
        selected["relative_path"],
        current_directory,
        items,
        gr.update(),
        gr.update(value=None, visible=False),
    )


def download_session_zip(session_root: Optional[str]):
    """Create a zip archive for the selected session."""
    if not session_root:
        return (
            gr.update(value=None, visible=False),
            StatusMessages.error("Error", "Select a session before creating an archive."),
        )

    download_tuple = download_session_api(session_root)
    if not download_tuple:
        return (
            gr.update(value=None, visible=False),
            StatusMessages.error("Error", "Failed to create session archive."),
        )

    zip_path, _filename = download_tuple
    return (
        gr.update(value=str(zip_path), visible=True),
        StatusMessages.success("Success", f"Session archive ready: {Path(zip_path).name}."),
    )


def create_session_artifacts_tab(demo):
    """Creates the Session Artifact Explorer tab."""
    with gr.Tab("Artifact Explorer"):
        gr.Markdown("## Session Artifact Explorer")

        selected_file_path = gr.State(value=None)
        current_directory_state = gr.State(value=None)
        artifact_rows_state = gr.State(value=[])
        session_state = gr.State(value=None)

        with gr.Row():
            session_picker = gr.Dropdown(
                label="Select a Session",
                info="Choose a session to view its artifacts."
            )
            refresh_button = gr.Button("Refresh Sessions")
            load_session_button = gr.Button("Load Session")

        with gr.Row():
            path_display = gr.Textbox(
                label="Current Path",
                interactive=False,
                placeholder="Select a session to begin.",
            )
            go_up_button = gr.Button("Go Up")
            download_session_button = gr.Button("Download Session Zip")
            session_zip_file = gr.File(label="Session Archive", visible=False)

        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### Artifacts")
                file_list = gr.DataFrame(
                    headers=COLUMNS,
                    datatype=["str", "str", "number", "str", "str", "str", "str"],
                    row_count=10,
                    col_count=(len(COLUMNS), "fixed"),
                    interactive=True,
                )
            with gr.Column(scale=3):
                gr.Markdown("### File Preview")
                file_preview = gr.Textbox(
                    label="File Content",
                    lines=15,
                    interactive=False,
                    placeholder="Select a text file to preview its content."
                )
                download_button = gr.File(label="Download Selected File", visible=False)

        status_display = gr.Markdown(value=StatusMessages.info("Ready", "Select a session to begin."))

        refresh_button.click(
            fn=refresh_sessions,
            outputs=[session_picker, status_display],
        )

        load_session_button.click(
            fn=on_session_selected,
            inputs=[session_picker],
            outputs=[
                file_list,
                status_display,
                file_preview,
                download_button,
                selected_file_path,
                current_directory_state,
                artifact_rows_state,
                path_display,
                session_zip_file,
                session_state,
            ],
        )

        go_up_button.click(
            fn=go_up_directory,
            inputs=[current_directory_state, session_state, artifact_rows_state],
            outputs=[
                file_list,
                status_display,
                file_preview,
                download_button,
                selected_file_path,
                current_directory_state,
                artifact_rows_state,
                path_display,
                session_zip_file,
            ],
        )

        file_list.select(
            fn=handle_artifact_selection,
            inputs=[artifact_rows_state, current_directory_state],
            outputs=[
                file_list,
                status_display,
                file_preview,
                download_button,
                selected_file_path,
                current_directory_state,
                artifact_rows_state,
                path_display,
                session_zip_file,
            ],
            show_progress="hidden",
        )

        download_session_button.click(
            fn=download_session_zip,
            inputs=[session_state],
            outputs=[session_zip_file, status_display],
        )

    return {
        "session_picker": session_picker,
        "refresh_button": refresh_button,
        "file_list": file_list,
        "file_preview": file_preview,
        "download_button": download_button,
        "status_display": status_display,
        "selected_file_path": selected_file_path,
        "current_directory_state": current_directory_state,
        "artifact_rows_state": artifact_rows_state,
        "path_display": path_display,
        "session_zip_file": session_zip_file,
        "session_state": session_state,
        "load_session_button": load_session_button,
    }
