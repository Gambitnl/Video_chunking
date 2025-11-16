# Session Artifact Explorer

The Session Artifact Explorer is a Gradio tab that calls the shared `SessionArtifactService`
API to browse, preview, and download the output files generated during session
processing.

## Features

- **Session Picker**: Lists every session detected under `output/`. The refresh button
  re-runs the API query without restarting the app.
- **Directory Navigation**: The artifacts grid shows both files and folders with their
  relative paths, size, created, and modified timestamps. Selecting a directory drills
  into it, and the “Go Up” button returns to the parent path.
- **Text Preview**: Uses the API’s preview endpoint to show the first 10 KB of text
  artifacts (`.txt`, `.md`, `.json`, `.log`, `.srt`, `.vtt`, etc.). Truncated previews
  are flagged automatically.
- **File Downloads**: Selecting a file exposes a download component wired to the API’s
  sandboxed `download_file` helper, so downloads never bypass the safety checks.
- **Session Archive**: The “Download Session Zip” button asks the backend to build a
  ZIP bundle for the current session and exposes it for download once ready.

## UI Entry Point

The explorer lives under the **Artifact Explorer** tab alongside the existing Gradio
tabs. Its components (dropdown, path indicator, artifact grid, preview pane, and
download widgets) react automatically as the API responses change.

## Workflow

1. Open the **Artifact Explorer** tab and click **Refresh Sessions** if you processed a
   session after launching the UI.
2. Pick a session from the dropdown and click **Load Session**; the current path display
   will show the session root (for example `20251115_184757_test_run`).
3. Browse the artifact grid:
   - Click a directory row (Directory column = “Yes”) to enter it.
   - Click **Go Up** to return to the parent directory.
4. Select a file row to:
   - View a preview (for supported text types) in the **File Preview** box.
   - Reveal a download link for the selected file.
5. Click **Download Session Zip** to build and download a complete archive of the
   session outputs.

All file and directory operations flow through the session artifact API, so the UI
inherits the same path-sandboxing and telemetry as the CLI.***
