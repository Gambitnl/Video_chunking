from __future__ import annotations

import gradio as gr


def create_logs_tab(blocks: gr.Blocks) -> None:
    def refresh_logs_ui(errors_only, num_lines):
        try:
            from src.logger import _logger_instance

            if errors_only:
                return _logger_instance.get_error_logs(lines=int(num_lines))
            return _logger_instance.get_recent_logs(lines=int(num_lines))
        except Exception as exc:
            return f"Error loading logs: {exc}"

    def clear_old_logs_ui():
        try:
            from src.logger import _logger_instance

            count = _logger_instance.clear_old_logs(days=7)
            return f"Cleared {count} old log file(s)"
        except Exception as exc:
            return f"Error clearing logs: {exc}"

    with gr.Tab("Logs"):
        gr.Markdown("""
        ### System Logs

        View application logs, errors, and processing history.
        """)

        with gr.Row():
            with gr.Column():
                refresh_logs_btn = gr.Button("Refresh Logs", size="sm")
                show_errors_only = gr.Checkbox(label="Show Errors/Warnings Only", value=False)
                log_lines = gr.Slider(
                    minimum=10,
                    maximum=500,
                    value=100,
                    step=10,
                    label="Number of lines to display",
                )

            with gr.Column():
                clear_old_logs_btn = gr.Button("Clear Old Logs (7+ days)", size="sm")
                clear_logs_status = gr.Textbox(label="Status", interactive=False)

        logs_output = gr.Textbox(
            label="Log Output",
            lines=20,
            max_lines=40,
            show_copy_button=True,
            interactive=False,
            elem_classes="scrollable-log",
        )

        refresh_logs_btn.click(
            fn=refresh_logs_ui,
            inputs=[show_errors_only, log_lines],
            outputs=[logs_output],
        )

        clear_old_logs_btn.click(
            fn=clear_old_logs_ui,
            outputs=[clear_logs_status],
        )

        blocks.load(
            fn=lambda: refresh_logs_ui(False, 100),
            outputs=[logs_output],
        )
