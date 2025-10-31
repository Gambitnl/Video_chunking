import gradio as gr
from src.ui.helpers import Placeholders, InfoText, StatusMessages, UIComponents
from src.ui.constants import StatusIndicators as SI

def create_dashboard_tab():
    """Creates the Campaign Dashboard tab and returns its components."""
    with gr.Tab("Campaign Dashboard"):
        gr.Markdown("""
        ### Campaign Overview & Health Check

        Select a campaign to see its complete configuration status and what data you have.
        """)
        
        with gr.Row():
            dashboard_campaign = gr.Dropdown(
                label="[CAMPAIGN] Select Campaign to Review",
                info="Choose which campaign to inspect"
            )
            dashboard_refresh = gr.Button(f"{SI.ACTION_REFRESH} Dashboard", variant="secondary", size="sm")

        dashboard_output = gr.Markdown()

    return dashboard_campaign, dashboard_refresh, dashboard_output