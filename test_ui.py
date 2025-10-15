"""Quick test to verify Party Management tab appears"""
import gradio as gr
from src.party_config import PartyConfigManager

party_manager = PartyConfigManager()
available_parties = ["Manual Entry"] + party_manager.list_parties()

print(f"Available parties: {available_parties}")

with gr.Blocks() as demo:
    gr.Markdown("# Test Party Management UI")

    with gr.Tab("Party Management"):
        gr.Markdown("### Import/Export Party Configurations")

        with gr.Row():
            with gr.Column():
                gr.Markdown("#### Export Party")
                export_party_dropdown = gr.Dropdown(
                    choices=available_parties,
                    label="Select Party to Export",
                    value="default"
                )
                export_btn = gr.Button("Export Party", variant="primary")
                export_status = gr.Textbox(label="Status", interactive=False)

            with gr.Column():
                gr.Markdown("#### Import Party")
                import_file = gr.File(label="Upload Party JSON File", file_types=[".json"])
                import_party_id = gr.Textbox(label="Party ID (optional)")
                import_btn = gr.Button("Import Party", variant="primary")
                import_status = gr.Textbox(label="Status", interactive=False)

if __name__ == "__main__":
    print("Starting test UI...")
    print("Open http://127.0.0.1:7861 to view")
    demo.launch(server_port=7861, share=False)
