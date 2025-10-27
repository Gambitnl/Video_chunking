from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional, Tuple

import gradio as gr
from src.ui.helpers import Placeholders, InfoText, StatusMessages, UIComponents
from src.ui.constants import StatusIndicators as SI

from src.google_drive_auth import (
    authenticate_automatically,
    exchange_code_for_token,
    get_auth_url,
    get_document_content,
    is_authenticated,
    revoke_credentials,
)


def create_document_viewer_tab(
    project_root: Path,
    set_notebook_context: Callable[[str], None],
    demo=None,
) -> None:
    def view_google_doc(doc_url):
        try:
            if not is_authenticated():
                return "Error: Not authenticated with Google Drive. Please authorize first using the 'Authorize Google Drive' section below."

            content = get_document_content(doc_url)
            if not content.startswith("Error"):
                set_notebook_context(content)
            return content
        except Exception as exc:
            return f"Error downloading document: {exc}"

    def check_auth_status():
        if is_authenticated():
            return "Status: Authenticated with Google Drive"
        return "Status: Not authenticated. Click 'Start Authorization' below."

    def start_oauth_flow() -> Tuple[str, Optional[object]]:
        try:
            auth_url, flow = get_auth_url()
            instructions = (
                f"Authorization URL generated!\n\n"
                f"Please follow these steps:\n"
                f"1. Click this link to authorize: {auth_url}\n\n"
                f"2. Sign in with your Google account and grant access\n"
                f"3. After granting access, your browser will try to redirect to localhost\n"
                f"   (the page won't load - this is normal!)\n"
                f"4. Copy the ENTIRE URL from your browser's address bar\n"
                f"   (it will look like: http://localhost:8080/?code=...&scope=...)\n"
                f"5. Paste the full URL below and click 'Complete Authorization'"
            )
            return instructions, flow
        except FileNotFoundError as exc:
            return str(exc), None
        except Exception as exc:
            return f"Error starting OAuth flow: {exc}", None

    def complete_oauth_flow(flow_object, auth_code: str):
        if not flow_object:
            return "Error: OAuth flow not started. Please click 'Start Authorization' first.", None

        if not auth_code or not auth_code.strip():
            return "Error: Please paste the authorization code.", flow_object

        success = exchange_code_for_token(flow_object, auth_code.strip())
        if success:
            return "Success! You are now authenticated with Google Drive. You can now load documents.", None
        return "Error: Failed to complete authorization. Please try again.", flow_object

    def revoke_oauth():
        revoke_credentials()
        return "Authentication revoked. You will need to authorize again to access documents."

    def start_automatic_oauth():
        success, message = authenticate_automatically()
        return message

    def open_setup_guide():
        guide_path = project_root / "docs" / "GOOGLE_OAUTH_SIMPLE_SETUP.md"

        if not guide_path.exists():
            return "Error: Setup guide not found. Please check docs/GOOGLE_OAUTH_SIMPLE_SETUP.md"

        try:
            if os.name == "nt":
                os.startfile(str(guide_path))
            elif os.name == "posix":
                subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", str(guide_path)])
            return f"[INFO] Opening setup guide: {guide_path.name}"
        except Exception as exc:
            return f"Guide location: {guide_path}\n(Could not auto-open: {exc})"

    with gr.Tab("Document Viewer"):
        gr.Markdown("""
        ### Google Drive Document Viewer

        View your private Google Docs without needing to make them publicly shared.

        **First-time setup (5-10 minutes, completely free):**
        1. Create Google Cloud credentials [INFO] See **`docs/GOOGLE_OAUTH_SIMPLE_SETUP.md`** for step-by-step guide
        2. Click "Authorize with Google" below
        3. Load any Google Doc you have access to!

        **Features:**
        - Access your private documents securely via OAuth
        - No need to make documents publicly shared
        - Import campaign notes for use in profile extraction and knowledge base
        - **No billing required** - completely free for personal use!
        """)

        oauth_flow_state = gr.State(None)

        gr.Markdown("### Authorization")

        with gr.Row():
            with gr.Column(scale=3):
                auth_status = gr.Textbox(
                    label="Current Status",
                    value="Checking...",
                    interactive=False,
                )
            with gr.Column(scale=1):
                setup_guide_btn = gr.Button("[GUIDE] Open Setup Guide", size="sm", variant="secondary")
                setup_guide_result = gr.Textbox(
                    label="",
                    value="",
                    interactive=False,
                    visible=False,
                    show_label=False,
                )

        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("""
                **Quick Setup (Recommended):**
                Click the button below - your browser will open for Google authorization.
                Just approve access and return here. That's it!
                """)
                auto_auth_btn = gr.Button(
                    "[AUTH] Authorize with Google",
                    variant="primary",
                    size="lg",
                )
                auto_auth_result = gr.Textbox(
                    label="Authorization Result",
                    lines=3,
                    interactive=False,
                )
            with gr.Column(scale=1):
                check_auth_btn = gr.Button("[STATUS] Check Status", size="sm")
                revoke_auth_btn = gr.Button("[REVOKE] Revoke Authorization", variant="secondary", size="sm")

        with gr.Accordion("Advanced: Manual Authorization (if automatic doesn't work)", open=False):
            gr.Markdown(
                """
            Use this method if the automatic authorization doesn't work (e.g., browser doesn't open automatically).
            """
            )
            with gr.Row():
                with gr.Column():
                    start_auth_btn = gr.Button("Start Manual Authorization", variant="secondary")
                    revoke_auth_btn_manual = gr.Button("Revoke Authorization", variant="secondary", size="sm")
                with gr.Column():
                    auth_output = gr.Textbox(
                        label="Authorization Instructions",
                        lines=8,
                        interactive=False,
                    )

            with gr.Row():
                with gr.Column():
                    auth_code_input = gr.Textbox(
                        label="Redirect URL or Authorization Code",
                        placeholder="Paste the full redirect URL from your browser (http://localhost:8080/?code=...)",
                        lines=2,
                    )
                    complete_auth_btn = gr.Button("Complete Authorization", variant="primary")
                with gr.Column():
                    auth_result = gr.Textbox(
                        label="Result",
                        lines=3,
                        interactive=False,
                    )

        gr.Markdown("### Load Google Document")
        gdoc_url_input = gr.Textbox(
            label="Google Doc URL",
            placeholder="Paste a Google Docs link (must have access with your authenticated account).",
        )
        gdoc_view_btn = gr.Button("Load Document", variant="primary")
        gdoc_output = gr.Markdown(label="Document Content")

        setup_guide_btn.click(
            fn=open_setup_guide,
            outputs=[setup_guide_result],
        )

        check_auth_btn.click(
            fn=check_auth_status,
            outputs=[auth_status],
        )

        auto_auth_btn.click(
            fn=start_automatic_oauth,
            outputs=[auto_auth_result],
        )

        revoke_auth_btn.click(
            fn=revoke_oauth,
            outputs=[auto_auth_result],
        )

        start_auth_btn.click(
            fn=start_oauth_flow,
            outputs=[auth_output, oauth_flow_state],
        )

        complete_auth_btn.click(
            fn=complete_oauth_flow,
            inputs=[oauth_flow_state, auth_code_input],
            outputs=[auth_result, oauth_flow_state],
        )

        revoke_auth_btn_manual.click(
            fn=revoke_oauth,
            outputs=[auth_result],
        )

        gdoc_view_btn.click(
            fn=view_google_doc,
            inputs=[gdoc_url_input],
            outputs=[gdoc_output],
        )

        # Load auth status when tab is opened (if demo object is available)
        if demo:
            demo.load(
                fn=check_auth_status,
                outputs=[auth_status],
            )