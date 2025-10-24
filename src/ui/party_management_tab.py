"""Party Management tab UI construction."""
from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Tuple

import gradio as gr

from src.party_config import PartyConfigManager


def create_party_management_tab(available_parties: List[str]) -> None:
    """Create the Party Management tab."""
    party_manager = PartyConfigManager()

    with gr.Tab("Party Management"):
        gr.Markdown(
            """
            ### Manage Your D&D Parties

            Save, export, and import party configurations to reuse them across sessions.

            #### Why Use Party Configurations?
            - Save time by avoiding manual entry for every session
            - Ensure consistent spelling of character and player names
            - Improve IC/OOC accuracy with richer metadata
            """
        )

        with gr.Row():
            with gr.Column():
                gr.Markdown("#### Export Party")
                export_party_choices = [p for p in available_parties if p != "Manual Entry"]
                export_party_dropdown = gr.Dropdown(
                    choices=export_party_choices,
                    label="Select Party to Export",
                    value=(
                        "default"
                        if "default" in export_party_choices
                        else (export_party_choices[0] if export_party_choices else None)
                    ),
                )
                export_btn = gr.Button("Export Party", variant="primary")
                export_output = gr.File(label="Download Party File")
                export_status = gr.Textbox(label="Status", interactive=False)

            with gr.Column():
                gr.Markdown("#### Import Party")
                import_file = gr.File(
                    label="Upload Party JSON File",
                    file_types=[".json"],
                )
                import_party_id = gr.Textbox(
                    label="Party ID (optional)",
                    placeholder="Leave empty to use ID from file",
                )
                import_btn = gr.Button("Import Party", variant="primary")
                import_status = gr.Textbox(label="Status", interactive=False)

        def export_party_ui(party_id: str) -> Tuple[Path | None, str]:
            if not party_id:
                return None, "Please select a party to export."
            try:
                temp_file = NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
                temp_path = Path(temp_file.name)
                temp_file.close()
                party_manager.export_party(party_id, temp_path)
                return temp_path, f"Exported '{party_id}'."
            except Exception as exc:  # pragma: no cover - UI handler
                return None, f"Error exporting party: {exc}"

        def import_party_ui(file_obj, party_id_override: str | None) -> str:
            if file_obj is None:
                return "Please upload a party JSON file."
            try:
                imported_id = party_manager.import_party(
                    Path(file_obj.name),
                    party_id_override or None,
                )
                return (
                    f"Successfully imported party '{imported_id}'. "
                    "Refresh the page to use the updated list."
                )
            except Exception as exc:  # pragma: no cover - UI handler
                return f"Error importing party: {exc}"

        export_btn.click(
            fn=export_party_ui,
            inputs=[export_party_dropdown],
            outputs=[export_output, export_status],
        )

        import_btn.click(
            fn=import_party_ui,
            inputs=[import_file, import_party_id],
            outputs=[import_status],
        )
