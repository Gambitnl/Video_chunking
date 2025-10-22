"""Simple Gradio landing page to control the session processor."""
import atexit
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict
import gradio as gr
from src.logger import get_log_file_path
from src.status_tracker import StatusTracker, STAGES
PROJECT_ROOT = Path(__file__).resolve().parent
APP_COMMAND = [sys.executable, "app.py"]
APP_PORT = int(os.getenv("SESSION_APP_PORT", "7860"))
MANAGER_PORT = int(os.getenv("SESSION_MANAGER_PORT", "7861"))
OPTION_LABELS = {
    "input_file": "Input file",
    "base_output_dir": "Base output directory",
    "session_output_dir": "Session output directory",
    "num_speakers": "Expected speakers",
    "using_party_config": "Using party configuration",
    "party_id": "Party identifier",
    "character_names": "Character names",
    "character_names_provided": "Character names provided",
    "player_names": "Player names",
    "player_names_provided": "Player names provided",
    "skip_diarization": "Skip speaker diarization",
    "skip_classification": "Skip IC/OOC classification",
    "skip_snippets": "Skip audio snippets",
    "party_context_available": "Party context available",
}

FLOWCHART_PATH = PROJECT_ROOT / "docs" / "pipeline_flowchart.svg"

_state: Dict[str, object] = {
    "process": None,
    "log_handle": None,
}
def _close_log_handle() -> None:
    handle = _state.get("log_handle")
    if handle:
        try:
            handle.close()
        finally:
            _state["log_handle"] = None
def _refresh_process_handle() -> None:
    proc: subprocess.Popen | None = _state.get("process")  # type: ignore[assignment]
    if proc and proc.poll() is not None:
        _close_log_handle()
        _state["process"] = None
def _is_app_listening() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", APP_PORT), timeout=0.5):
            return True
    except OSError:
        return False
def _status_lines(header: str = "Status") -> str:
    def format_value(value):
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, dict):
            if not value:
                return "(none)"
            parts = [f"{key}={format_value(val)}" for key, val in value.items()]
            return ", ".join(parts)
        if isinstance(value, list):
            return ", ".join(str(item) for item in value) if value else "(none)"
        if value in (None, "", []):
            return "(not provided)"
        return str(value)
    def format_option_line(key: str, value) -> str:
        label = OPTION_LABELS.get(key, key.replace("_", " ").title())
        return f"- {label}: {format_value(value)}"
    def format_stage(stage: Dict[str, object]) -> str:
        state = str(stage.get("state", "pending"))
        label = str(stage.get("name", f"Stage {stage.get('id')}") )
        prefix_map = {
            "completed": "[done]",
            "running": "[run ]",
            "skipped": "[skip]",
            "failed": "[fail]",
        }
        prefix = prefix_map.get(state, "[todo]")
        started = stage.get("started_at")
        ended = stage.get("ended_at")
        duration = stage.get("duration_seconds")
        segments = []
        if started:
            segments.append(f"start {started}")
        if ended:
            segments.append(f"end {ended}")
        elif state == "running" and started:
            segments.append("in progress")
        if isinstance(duration, (int, float)):
            segments.append(f"duration {duration}s")
        detail = f" | {', '.join(segments)}" if segments else ""
        message = stage.get("message") or ""
        line = f"- {prefix} {label}{detail}"
        if message:
            line += f" - {message}"
        details = stage.get("details")
        if details:
            line += f" (details: {format_value(details)})"
        return line
    _refresh_process_handle()
    running = (_state.get("process") is not None) or _is_app_listening()
    lines = [f"### {header}", ""]
    lines.append("**App is running**" if running else "**App is stopped**")
    proc: subprocess.Popen | None = _state.get("process")  # type: ignore[assignment]
    if proc and proc.poll() is None:
        lines.append(f"- PID: `{proc.pid}`")
    lines.append(f"- Endpoint: http://127.0.0.1:{APP_PORT}")
    lines.append(f"- Log file: `{get_log_file_path()}`")
    log_stdout = PROJECT_ROOT / "logs" / "app_stdout.log"
    lines.append(f"- App stdout: `{log_stdout}`")
    snapshot = StatusTracker.get_snapshot()
    if not running:
        lines.append("- Status tracker: idle (app not running)")
        lines.append("- Use Start App to launch the processing UI.")
        if snapshot and snapshot.get("session_id"):
            lines.append("")
            lines.append(f"_Last completed session:_ `{snapshot.get('session_id')}`")
            lines.append(f"- Result: {snapshot.get('status', 'unknown')}")
        return "\n".join(lines)
    if snapshot is None:
        snapshot = {
            "processing": False,
            "stages": [
                {"id": stage["id"], "name": stage["name"], "state": "pending", "message": ""}
                for stage in STAGES
            ],
        }
    lines.append("")
    session_id = snapshot.get("session_id") or "unknown"
    status_text = snapshot.get("status", "unknown")
    lines.append(f"**Session:** `{session_id}`")
    lines.append(f"- Status: {status_text}")
    updated_at = snapshot.get("updated_at")
    if updated_at:
        lines.append(f"- Last update: {updated_at}")
    if not snapshot.get("processing"):
        if snapshot.get("completed_at"):
            lines.append(f"- Last finished at: {snapshot.get('completed_at')}")
        lines.append("- No session currently processing.")
        return "\n".join(lines)
    started_at = snapshot.get("started_at")
    completed_at = snapshot.get("completed_at")
    duration_s = snapshot.get("duration_seconds")
    if started_at:
        lines.append(f"- Started: {started_at}")
    if completed_at:
        lines.append(f"- Finished: {completed_at}")
    if isinstance(duration_s, (int, float)):
        lines.append(f"- Total duration: {duration_s}s")
    current_id = snapshot.get("current_stage")
    if current_id:
        current_name = next((s["name"] for s in STAGES if s["id"] == current_id), None)
        if current_name:
            lines.append(f"- Current stage: {current_name}")
    if snapshot.get("error"):
        lines.append(f"- Error: {snapshot.get('error')}")
    options = snapshot.get("options") or {}
    if options:
        lines.append("")
        lines.append("#### Session Options")
        for key in sorted(options.keys()):
            lines.append(format_option_line(key, options[key]))
    events = snapshot.get("events") or []
    if events:
        lines.append("")
        lines.append("#### Recent Events")
        for event in events[-8:]:
            timestamp = event.get("timestamp") or ""
            stage_name = event.get("stage_name") or "Stage"
            event_type = event.get("event") or "update"
            message = event.get("message") or ""
            descriptor = f"{timestamp} | {stage_name} | {event_type}"
            if message:
                descriptor += f": {message}"
            lines.append(f"- {descriptor}")
    stages = snapshot.get("stages", [])
    if stages:
        lines.append("")
        lines.append("#### Pipeline Stages")
        for stage in stages:
            lines.append(format_stage(stage))
        return "\n".join(lines)

def _flowchart_initial_state():
    if FLOWCHART_PATH.exists():
        return ("Latest flowchart available.", str(FLOWCHART_PATH), True)
    return ("No flowchart generated yet. Click the button below to create one.", None, False)


def _generate_pipeline_flowchart():
    try:
        from graphviz import Digraph
        from graphviz.backend import execute
    except ImportError:
        return (
            "Graphviz Python package missing. Run `pip install graphviz` and ensure Graphviz binaries are installed.",
            None,
        )

    potential_dot = PROJECT_ROOT / "tools" / "graphviz" / "Graphviz-14.0.2-win64" / "bin" / "dot.exe"
    if potential_dot.exists():
        os.environ["PATH"] = f"{potential_dot.parent}{os.pathsep}" + os.environ.get("PATH", "")
        os.environ.setdefault("GRAPHVIZ_DOT", str(potential_dot))

    dot = Digraph("Pipeline", graph_attr={"rankdir": "LR", "splines": "spline"})
    dot.attr("node", shape="rectangle", style="rounded,filled", color="#0C111F", fillcolor="#161B26", fontname="Helvetica", fontcolor="#E2E8F0")
    dot.attr("edge", color="#718096", arrowsize="0.8")

    if not STAGES:
        dot.node("No stages defined")
    else:
        dot.edge("Audio Input", STAGES[0]["name"])
        for i in range(len(STAGES) - 1):
            src = STAGES[i]["name"]
            dst = STAGES[i + 1]["name"]
            dot.edge(src, dst)

    FLOWCHART_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_base = FLOWCHART_PATH.with_suffix("")

    try:
        rendered = Path(dot.render(str(output_base), format="svg", cleanup=True))
    except execute.ExecutableNotFound:
        return (
            "Graphviz executable `dot` not found. Install Graphviz (https://graphviz.org/download/) and ensure it is on PATH.",
            None,
        )
    except Exception as exc:
        return (f"Error generating flowchart: {exc}", None)

    return (f"Flowchart updated: {rendered}", str(rendered))


def _generate_flowchart_ui():
    status, image_path = _generate_pipeline_flowchart()
    return status, gr.update(value=image_path, visible=bool(image_path))


def start_app():
    _refresh_process_handle()
    proc: subprocess.Popen | None = _state.get("process")  # type: ignore[assignment]
    if proc and proc.poll() is None:
        return _status_lines("Already running")
    if _is_app_listening():
        return _status_lines("Detected running instance")
    logs_dir = PROJECT_ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)
    stdout_path = logs_dir / "app_stdout.log"
    log_handle = stdout_path.open("a", encoding="utf-8", buffering=1)
    process = subprocess.Popen(
        APP_COMMAND,
        cwd=str(PROJECT_ROOT),
        stdout=log_handle,
        stderr=log_handle,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    _state["process"] = process
    _state["log_handle"] = log_handle
    time.sleep(1)
    return _status_lines("Start requested")
def stop_app():
    _refresh_process_handle()
    proc: subprocess.Popen | None = _state.get("process")  # type: ignore[assignment]
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        finally:
            _close_log_handle()
            _state["process"] = None
    deadline = time.time() + 5
    while _is_app_listening() and time.time() < deadline:
        time.sleep(0.2)
    snapshot = StatusTracker.get_snapshot()
    if snapshot and snapshot.get("processing"):
        session_id = snapshot.get("session_id") or "unknown"
        StatusTracker.fail_session(session_id, "Stopped via dashboard")
    return _status_lines("Stop requested")
def refresh_status():
    return _status_lines()
def main():
    with gr.Blocks(title="Session Processor Manager") as demo:
        status_md = gr.Markdown(refresh_status())
        with gr.Row():
            start_btn = gr.Button("Start App", variant="primary")
            stop_btn = gr.Button("Stop App", variant="stop")
            refresh_btn = gr.Button("Refresh Status")
        demo.load(fn=refresh_status, outputs=status_md)
        status_timer = gr.Timer(value=2.0)
        status_timer.tick(fn=refresh_status, outputs=status_md)
        start_btn.click(fn=start_app, outputs=status_md)
        stop_btn.click(fn=stop_app, outputs=status_md)
        refresh_btn.click(fn=refresh_status, outputs=status_md)
        gr.Markdown(
            "Use this dashboard to launch or stop `app.py`. "
            "The processor must remain running for the main interface at "
            f"http://127.0.0.1:{APP_PORT}."
        )
        with gr.Tabs():
            with gr.Tab("Pipeline Flowchart"):
                initial_status, initial_image, initial_visible = _flowchart_initial_state()
                flowchart_status = gr.Markdown(initial_status)
                flowchart_image = gr.Image(value=initial_image, visible=initial_visible, label="Pipeline Flowchart")
                generate_btn = gr.Button("Generate Flowchart", variant="primary")

                generate_btn.click(
                    fn=_generate_flowchart_ui,
                    outputs=[flowchart_status, flowchart_image]
                )

            demo.queue()
    demo.launch(server_name="127.0.0.1", server_port=MANAGER_PORT, show_error=True)
@atexit.register
def _cleanup_on_exit():
    stop_app()
if __name__ == "__main__":
    main()