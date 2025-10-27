from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import gradio as gr
import subprocess
from src.ui.helpers import Placeholders, InfoText, StatusMessages, UIComponents
from src.ui.constants import StatusIndicators as SI


def _collect_pytest_nodes(project_root: Path) -> Tuple[List[str], str]:
    try:
        result = subprocess.run(
            ["pytest", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "pytest not found. Install dev dependencies (pip install -r requirements.txt)."
        ) from exc

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode != 0:
        combined = stderr or stdout or f"pytest exited with status {result.returncode}"
        raise RuntimeError(combined)

    nodes = [
        line.strip()
        for line in stdout.splitlines()
        if line.strip() and not line.startswith("<") and "::" in line
    ]
    return nodes, stderr


def _run_pytest(project_root: Path, args: List[str]) -> Tuple[str, str]:
    try:
        result = subprocess.run(
            ["pytest", *args],
            capture_output=True,
            text=True,
            cwd=str(project_root),
        )
    except FileNotFoundError:
        return (
            "pytest not found. Install dev dependencies (pip install -r requirements.txt).",
            "",
        )

    combined = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    combined = combined.strip() or "(no output)"

    max_len = 5000
    if len(combined) > max_len:
        combined = "... (output truncated)\n" + combined[-max_len:]

    status = (
        "PASS: Tests succeeded"
        if result.returncode == 0
        else f"FAIL: Tests exited with code {result.returncode}"
    )
    return status, combined


def create_diagnostics_tab(project_root: Path) -> None:
    def collect_pytest_tests_ui():
        try:
            nodes, warnings = _collect_pytest_nodes(project_root)
        except RuntimeError as exc:
            message = f"Warning: Unable to collect tests:\n```\n{exc}\n```"
            return message, gr.update(choices=[], value=[])

        if not nodes:
            return (
                "No pytest tests discovered in this repository.",
                gr.update(choices=[], value=[]),
            )

        message = f"Discovered {len(nodes)} tests. Select entries to run individually."
        if warnings:
            message += f"\n\nWarnings:\n```\n{warnings}\n```"

        return message, gr.update(choices=nodes, value=[])

    def run_pytest_selection(selected_tests):
        if not selected_tests:
            return "Select at least one test to run.", ""

        return _run_pytest(project_root, ["-q", *selected_tests])

    def run_all_tests_ui():
        return _run_pytest(project_root, ["-q"])

    with gr.Tab("Diagnostics"):
        gr.Markdown("""
        ### Test Diagnostics

        Discover pytest tests and run them without leaving the app.

        **Buttons**
        - **Discover Tests**: Runs `pytest --collect-only -q` and populates the list with discoverable test node IDs.
        - **Run Selected Tests**: Executes the chosen node IDs with `pytest -q`, returning pass/fail plus truncated output.
        - **Run All Tests**: Launches the entire pytest suite (`pytest -q`) for a quick regression check.

        **Notes**
        - Requires the development dependencies from `requirements.txt` (pytest, etc.).
        - Output is capped to keep the UI responsive; open `logs/app_stdout.log` if you need the full trace.
        - Use this tab while iterating on pipeline components to validate fixes without leaving the dashboard.
        """)
        discover_btn = gr.Button("Discover Tests", variant="secondary")
        tests_list = gr.CheckboxGroup(label="Available Tests", choices=[], interactive=True)
        with gr.Row():
            run_selected_btn = gr.Button("Run Selected Tests", variant="primary")
            run_all_btn = gr.Button("Run All Tests", variant="secondary")
        test_status = gr.Markdown("")
        test_output = gr.Textbox(label="Pytest Output", value="", lines=12, interactive=False)

        discover_btn.click(
            fn=collect_pytest_tests_ui,
            outputs=[test_status, tests_list],
        )

        run_selected_btn.click(
            fn=run_pytest_selection,
            inputs=[tests_list],
            outputs=[test_status, test_output],
        )

        run_all_btn.click(
            fn=run_all_tests_ui,
            outputs=[test_status, test_output],
        )
