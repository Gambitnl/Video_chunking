from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import gradio as gr

from src.config import Config
from src.ui.constants import StatusIndicators
from src.ui.helpers import StatusMessages, Placeholders
from src.story_notebook import StoryNotebookManager, StorySessionData

STORY_NO_DATA = "No transcription data available for this session yet."


def _session_from_state(session_state: Dict) -> StorySessionData:
    return StorySessionData(
        session_id=session_state.get("session_id", "session"),
        json_path=Path(session_state.get("json_path", Config.OUTPUT_DIR)),
        metadata=session_state.get("metadata", {}),
        segments=session_state.get("segments", []),
    )


def create_story_notebook_tab(
    story_manager: StoryNotebookManager,
    get_notebook_context: Callable[[], str],
    get_notebook_status: Callable[[], str],
) -> None:
    def _prepare_session_outputs(
        session_id: Optional[str],
        session_choices: List[str],
    ) -> Tuple[dict, dict, str, Dict, str]:
        notebook_status = get_notebook_status()
        selected = session_id if session_id in session_choices else (
            session_choices[0] if session_choices else None
        )
        session_dropdown = gr.update(choices=session_choices, value=selected)

        if not selected:
            message = StatusMessages.warning(
                "No Sessions Available",
                STORY_NO_DATA,
                "Process a session with the pipeline, then click Refresh Sessions."
            )
            return (
                session_dropdown,
                gr.update(choices=[], value=None, interactive=False),
                message,
                {},
                notebook_status,
            )

        try:
            session = story_manager.load_session(selected)
        except FileNotFoundError:
            message = StatusMessages.warning(
                "Session Not Found",
                STORY_NO_DATA,
                f"Could not locate processed data for {selected!r}. Re-run the pipeline and refresh."
            )
            return (
                session_dropdown,
                gr.update(choices=[], value=None, interactive=False),
                message,
                {},
                notebook_status,
            )
        except Exception as exc:
            message = StatusMessages.error(
                "Failed to Load Session",
                f"An unexpected error occurred while loading {selected!r}.",
                str(exc)
            )
            return (
                session_dropdown,
                gr.update(choices=[], value=None, interactive=False),
                message,
                {},
                notebook_status,
            )

        character_names = session.character_names
        character_dropdown = gr.update(
            choices=character_names,
            value=(character_names[0] if character_names else None),
            interactive=bool(character_names),
        )

        if not session.segments:
            message = StatusMessages.warning(
                "No Segment Data",
                STORY_NO_DATA,
                "The selected session file is missing segment data."
            )
        else:
            details = story_manager.build_session_info(session)
            message = StatusMessages.success("Session Ready", details)

        session_state: Dict = {
            "session_id": session.session_id,
            "json_path": str(session.json_path),
            "metadata": session.metadata,
            "segments": session.segments,
        }

        return (
            session_dropdown,
            character_dropdown,
            message,
            session_state,
            notebook_status,
        )

    initial_sessions = story_manager.list_sessions()
    (
        initial_session_update,
        initial_character_update,
        initial_message,
        initial_session_state,
        initial_notebook_status,
    ) = _prepare_session_outputs(None, initial_sessions)

    initial_dropdown_choices = getattr(initial_session_update, "choices", initial_sessions)
    initial_dropdown_value = getattr(initial_session_update, "value", initial_sessions[0] if initial_sessions else None)

    initial_character_choices = getattr(initial_character_update, "choices", [])
    initial_character_value = getattr(initial_character_update, "value", None)
    initial_character_interactive = getattr(initial_character_update, "interactive", bool(initial_character_choices))

    story_session_state = gr.State(initial_session_state)

    def story_refresh_sessions_ui() -> Tuple[dict, dict, str, Dict, str]:
        sessions = story_manager.list_sessions()
        return _prepare_session_outputs(None, sessions)

    def story_select_session_ui(session_id: Optional[str]) -> Tuple[dict, dict, str, Dict, str]:
        sessions = story_manager.list_sessions()
        return _prepare_session_outputs(session_id, sessions)

    def story_generate_narrator(session_state: Dict, temperature: float) -> Tuple[str, str]:
        if not session_state or not session_state.get("segments"):
            return (
                StatusMessages.warning(
                    "No Session Loaded",
                    "Please select a session from the dropdown above, then try again."
                ),
                "",
            )

        try:
            session = _session_from_state(session_state)
            story, file_path = story_manager.generate_narrator(
                session,
                notebook_context=get_notebook_context(),
                temperature=temperature,
            )
            return story, str(file_path) if file_path else ""
        except Exception as exc:
            error_msg = StatusMessages.error(
                "Narrative Generation Failed",
                "Unable to generate the narrator perspective for this session.",
                str(exc)
            )
            return error_msg, ""

    def story_generate_character(session_state: Dict, character_name: str, temperature: float) -> Tuple[str, str]:
        if not session_state or not session_state.get("segments"):
            return (
                StatusMessages.warning(
                    "No Session Loaded",
                    "Please select a session from the dropdown at the top of this tab, then try again."
                ),
                "",
            )
        if not character_name:
            return (
                StatusMessages.warning(
                    "No Character Selected",
                    "Choose a character perspective before generating the narrative."
                ),
                "",
            )

        try:
            session = _session_from_state(session_state)
            story, file_path = story_manager.generate_character(
                session,
                character_name=character_name,
                notebook_context=get_notebook_context(),
                temperature=temperature,
            )
            return story, str(file_path) if file_path else ""
        except Exception as exc:
            error_msg = StatusMessages.error(
                "Character Narrative Failed",
                f"Unable to generate the narrative from {character_name}'s perspective.",
                str(exc)
            )
            return error_msg, ""

    def refresh_notebook_status() -> str:
        return get_notebook_status()

    with gr.Tab("Story Notebooks"):
        gr.Markdown("""
        ### Story Notebooks - Generate Session Narratives

        Transform your processed session transcripts into compelling story narratives using AI.

        #### How It Works:

        1. **Select a Session**: Choose a processed session from the dropdown
        2. **Adjust Creativity**: Lower = faithful retelling (0.1-0.4), Higher = more dramatic flair (0.6-1.0)
        3. **Generate Narrator Summary**: Creates an omniscient overview of the session (DM perspective)
        4. **Generate Character Narratives**: Creates first-person recaps from each PC's point of view

        #### What You Get:

        - **Narrator Perspective**: A balanced, objective summary highlighting all characters' contributions
        - **Character Perspectives**: Personal, emotional accounts from each character's viewpoint
        - **Campaign Continuity**: References your campaign notebook (if loaded) for context
        - **Saved Narratives**: All narratives are saved to `output/<session>/narratives/` folder

        #### Tips:

        - **First run?** Click "Refresh Sessions" to load available sessions
        - **Want more context?** Use the Document Viewer tab to import campaign notes first
        - **Creativity slider**: 0.3-0.5 works well for accurate summaries, 0.6-0.8 for dramatic storytelling
        - **Save time**: Generate narrator first to get the big picture, then character perspectives

        ---
        """)

        story_session_dropdown = gr.Dropdown(
            label="Session",
            choices=initial_dropdown_choices,
            value=initial_dropdown_value,
            interactive=True,
            info="Select which processed session to summarize",
        )
        refresh_story_btn = UIComponents.create_action_button(SI.ACTION_REFRESH, variant="secondary")
        story_temperature = gr.Slider(
            minimum=0.1,
            maximum=1.0,
            value=0.55,
            step=0.05,
            label="Creativity",
            info="Lower = faithful retelling, higher = more flourish",
        )

        story_notebook_status = gr.Markdown(initial_notebook_status)
        story_session_info = gr.Markdown(initial_message)

        with gr.Accordion("Narrator Perspective", open=True):
            narrator_btn = UIComponents.create_action_button("Generate Narrator Summary", variant="primary")
            narrator_story = gr.Markdown(
                StatusMessages.info("Narrator Perspective", "Narrator perspective will appear here once generated.")
            )
            narrator_path = gr.Textbox(
                label="Saved Narrative Path",
                interactive=False,
                placeholder="Path will appear after generation",
            )

        with gr.Accordion("Character Perspectives", open=False):
            character_dropdown = gr.Dropdown(
                label="Select Character",
                choices=initial_character_choices,
                value=initial_character_value,
                interactive=initial_character_interactive,
                info="Choose which character voice to write from",
            )
            character_btn = UIComponents.create_action_button("Generate Character Narrative", variant="primary")
            character_story = gr.Markdown(
                StatusMessages.info(
                    "Character Narrative",
                    "Pick a character and generate to see their perspective."
                )
            )
            character_path = gr.Textbox(
                label="Saved Narrative Path",
                interactive=False,
                placeholder="Path will appear after generation",
            )

        def _prepare_narrator_generation():
            return (
                StatusMessages.loading("Generating narrator summary"),
                ""
            )

        def _prepare_character_generation():
            return (
                StatusMessages.loading("Generating character narrative"),
                ""
            )

        refresh_notebook_btn = UIComponents.create_action_button("Refresh Notebook Context", variant="secondary")

        refresh_story_btn.click(
            fn=story_refresh_sessions_ui,
            outputs=[
                story_session_dropdown,
                character_dropdown,
                story_session_info,
                story_session_state,
                story_notebook_status,
            ],
        )

        story_session_dropdown.change(
            fn=story_select_session_ui,
            inputs=[story_session_dropdown],
            outputs=[
                character_dropdown,
                story_session_info,
                story_session_state,
                story_notebook_status,
            ],
        )

        narrator_btn.click(
            fn=_prepare_narrator_generation,
            outputs=[narrator_story, narrator_path],
            queue=True,
        ).then(
            fn=story_generate_narrator,
            inputs=[story_session_state, story_temperature],
            outputs=[narrator_story, narrator_path],
            queue=True,
        )

        character_btn.click(
            fn=_prepare_character_generation,
            outputs=[character_story, character_path],
            queue=True,
        ).then(
            fn=story_generate_character,
            inputs=[story_session_state, character_dropdown, story_temperature],
            outputs=[character_story, character_path],
            queue=True,
        )

        refresh_notebook_btn.click(
            fn=refresh_notebook_status,
            outputs=[story_notebook_status],
        )
