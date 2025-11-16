# Feature Request: Session Artifact Explorer

## Summary
Operators need a single place to browse, preview, and download every artifact generated for a processed session (e.g., `output/20251115_184757_test_s6_nov15_1847pm`). Today, verifying outputs means jumping into the filesystem, manually opening multiple files, and guessing which transcript or JSON is current. A built-in content viewer that understands the session directory layout would streamline QA, debugging, and sharing deliverables.

## Goals & Outcomes
- Provide a file-browser style view scoped to one session directory with columns for name, size, file type, created and modified timestamps.
- Allow users to download the entire session as a zip bundle or download selected files individually.
- Surface high-level metadata (session id, campaign, stage status) so users know which run they are inspecting.

## Functional Requirements
1. **Session Picker**
   - List sessions discovered under `output/` (sorted by latest modified) with a search/filter input.
   - Selecting a session loads its directory tree.

2. **File Viewer Pane**
   - Display directory contents in a table with columns: `Name`, `Type` (based on extension), `Size` (human-readable), `Created`, `Modified`.
   - Support expanding subdirectories (e.g., `intermediates/`, `segments/`) without reloading the entire page.
   - When a row is selected:
     - If it is a text-based artifact (`.txt`, `.json`, `.md`, `.srt`), render a preview (first 5-10 KB) below the table with syntax highlighting for JSON.
     - For binary files, show metadata (size, path) and a download button.

3. **Download Controls**
   - "Download Session" action that zips the root folder and streams it to the user.
   - Per-file download buttons/actions exposed via row context menu.

4. **Metadata Sidebar**
   - Show session id, campaign id, stages completed, total runtime, and last processed timestamp (read from the session `_data.json` metadata block).
   - Include quick links to open the IC-only transcript or knowledge report in a new tab.

## Non-Functional Requirements
- **Performance**: Directory listing should feel instant (<500 ms for ~200 files). Cache file metadata per session until the folder changes.
- **Security**: Restrict browsing to the workspace `output/` tree to avoid leaking other files. Sanitize download paths.
- **Portability**: UI must work in both the modern Gradio app and any future desktop shell without OS-specific tooling.

## Open Questions
- Should previews stream entire JSON files or cap at a configurable size?
- Do we need inline diffing for multiple runs of the same session id?
- Is zipping large (>1 GB) sessions acceptable synchronously, or should we offload to a background worker with progress updates?

## Suggested Implementation Notes
- Introduce a `SessionArtifactService` that encapsulates directory scanning, metadata extraction, and zip generation.
- Reuse existing metadata from `*_data.json` to avoid recomputing stats.
- In the UI layer, build a reusable table component so the CLI (text-only) can also render the same data via `rich`.
- Add integration tests that mock a sample session directory and assert the API returns the expected tree + metadata.

## Acceptance Criteria
- User can pick a processed session and see every artifact with name/size/type/timestamps.
- Clicking a `.txt` or `.json` file shows an inline preview without downloading.
- User can download either a single file or the entire session bundle.
- Unauthorized paths (e.g., using `..`) are blocked and logged.
