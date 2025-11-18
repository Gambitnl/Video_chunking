# Session Artifact Explorer

The Session Artifact Explorer is a Gradio tab powered by the shared
`SessionArtifactService`. It lets you browse, preview, download, and delete the output
artifacts generated during session processing without leaving the app.

## Features

- **Session Picker**: Lists every session under `output/`. The refresh button re-runs
  the API query so new sessions appear without restarting the UI.
- **Directory Navigation**: The artifact grid shows both files and folders with their
  relative paths, sizes, and timestamps. Selecting a directory drills into it, while
  the **Go Up** button returns to the parent path.
- **Text Preview**: Uses the API's preview endpoint to show the first 10 KB of common
  text formats (`.txt`, `.md`, `.json`, `.log`, `.srt`, `.vtt`, etc.). Truncated previews
  are flagged automatically.
- **File Downloads**: Selecting a file exposes a download widget wired to the API's
  sandboxed `download_file` helper, so files are always served from safe paths.
- **Session Archive**: The **Download Session Zip** button asks the backend to build a
  ZIP bundle for the entire session and exposes it when ready.
- **Deletion Controls**: Remove individual artifacts (files or folders) or purge the
  entire session directory. Deletions flow through the same sandboxed service, keeping
  the scope limited to `output/`.

## UI Entry Point

The explorer lives under the **Artifact Explorer** tab in the modern UI. Its components
(dropdown, path indicator, artifact grid, preview pane, and download widgets) react
whenever the API responses change.

## Workflow

1. Open the **Artifact Explorer** tab and click **Refresh Sessions** if you processed a
   session after launching the UI.
2. Select a session from the dropdown and click **Load Session**. The current path box
   will display the session root (for example `20251115_184757_test_run`).
3. Browse the artifact grid:
   - Click a directory row (Directory column = "Yes") to enter it.
   - Click **Go Up** to return to the parent directory.
4. Select a file row to:
   - Preview its content (if the format is supported) in the **File Preview** box.
   - Reveal a download link for that file.
5. Click **Download Session Zip** to build and download a complete archive of the
   session outputs.
6. Use **Delete Selected Artifact** to remove the highlighted file/folder, or **Delete
   Session** to remove the entire session directory (it disappears from the dropdown
   immediately).

All operations flow through the session artifact API, so the UI inherits the same
path-sandboxing, telemetry, and validation rules as the CLI.
