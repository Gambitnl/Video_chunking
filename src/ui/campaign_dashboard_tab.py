import gradio as gr

def create_dashboard_tab():
    """Creates the Campaign Dashboard tab and returns its components."""
    with gr.Tab("Campaign Dashboard"):
        gr.Markdown("""
        ### Campaign Overview & Health Check

        Select a campaign to see its complete configuration status and what data you have.
        """)
        
        with gr.Row():
            dashboard_campaign = gr.Dropdown(
                label="📋 Select Campaign to Review",
                info="Choose which campaign to inspect"
            )
            dashboard_refresh = gr.Button("🔄 Refresh Dashboard", variant="secondary", size="sm")

        dashboard_output = gr.Markdown()

    return dashboard_campaign, dashboard_refresh, dashboard_output