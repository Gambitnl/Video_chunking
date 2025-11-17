"""
UI helper utilities for consistent patterns across all Gradio tabs.
"""
from pathlib import Path
from typing import Optional, List
import gradio as gr

from src.ui.constants import StatusIndicators as SI


class StatusMessages:
    """Helper class for formatting consistent status messages across the UI."""

    @staticmethod
    def error(title: str, message: str, details: str = "") -> str:
        """
        Format an error message for display.

        Args:
            title: Error title
            message: Main error message
            details: Optional technical details (will be shown in code block)

        Returns:
            Markdown-formatted error message
        """
        md = f"**Error: {title}**\n\n{message}"
        if details:
            md += f"\n\n**Details:**\n```\n{details}\n```"
        return md

    @staticmethod
    def success(title: str, message: str, details: str = "") -> str:
        """
        Format a success message for display.

        Args:
            title: Success title
            message: Main success message
            details: Optional additional details

        Returns:
            Markdown-formatted success message
        """
        md = f"### {SI.SUCCESS} {title}\n\n{message}"
        if details:
            md += f"\n\n{details}"
        return md

    @staticmethod
    def warning(title: str, message: str, action: str = "") -> str:
        """
        Format a warning message for display.

        Args:
            title: Warning title
            message: Main warning message
            action: Optional recommended action

        Returns:
            Markdown-formatted warning message
        """
        md = f"### {SI.WARNING} {title}\n\n{message}"
        if action:
            md += f"\n\n**Recommended Action:** {action}"
        return md

    @staticmethod
    def info(title: str, message: str) -> str:
        """
        Format an info message for display.

        Args:
            title: Info title
            message: Main info message

        Returns:
            Markdown-formatted info message
        """
        return f"### {SI.INFO} {title}\n\n{message}"

    @staticmethod
    def loading(operation: str) -> str:
        """
        Format a loading message for display.

        Args:
            operation: Description of what's being loaded

        Returns:
            Markdown-formatted loading message
        """
        return f"### {SI.LOADING} Processing\n\n{operation}... Please wait."

    @staticmethod
    def empty_state(component_name: str, action_hint: str) -> str:
        """
        Format an empty state message.

        Args:
            component_name: Name of the component (e.g., "Campaign Library")
            action_hint: Hint for what user should do

        Returns:
            Markdown-formatted empty state message
        """
        return f"### {SI.INFO} {component_name}\n\n{action_hint}"


class FileValidation:
    """Helper class for validating file uploads."""

    @staticmethod
    def validate_file(
        file_obj,
        allowed_extensions: List[str],
        component_name: str = "This upload"
    ) -> Optional[str]:
        """
        Validate an uploaded file.

        Args:
            file_obj: File object from Gradio file upload
            allowed_extensions: List of allowed extensions (e.g., ['.txt', '.md'])
            component_name: Name of the component for error messages

        Returns:
            Error message if validation fails, None if valid
        """
        if file_obj is None:
            return StatusMessages.error(
                "No File Uploaded",
                f"{component_name} requires a file to be uploaded.",
                f"Accepted formats: {', '.join(allowed_extensions)}"
            )

        file_path = Path(file_obj.name)
        file_ext = file_path.suffix.lower()

        if file_ext not in allowed_extensions:
            return StatusMessages.error(
                "Invalid File Type",
                f"{component_name} does not accept {file_ext} files.",
                f"Accepted formats: {', '.join(allowed_extensions)}\n"
                f"Your file: {file_path.name}"
            )

        return None  # Valid

    @staticmethod
    def validate_file_size(file_obj, max_size_mb: int = 100) -> Optional[str]:
        """
        Validate file size.

        Args:
            file_obj: File object from Gradio
            max_size_mb: Maximum allowed size in MB

        Returns:
            Error message if too large, None if valid
        """
        if file_obj is None:
            return None

        try:
            file_size = Path(file_obj.name).stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            if file_size_mb > max_size_mb:
                return StatusMessages.error(
                    "File Too Large",
                    f"File size is {file_size_mb:.1f}MB but maximum allowed is {max_size_mb}MB.",
                    "Please compress or split your file before uploading."
                )
        except Exception:
            pass  # If we can't check size, don't block upload

        return None


class UIComponents:
    """Helper class for creating common UI component patterns."""

    @staticmethod
    def create_action_button(
        label: str,
        variant: str = "primary",
        size: str = "md",
        full_width: bool = False
    ) -> gr.Button:
        """
        Create a consistently-styled action button.

        Args:
            label: Button label (plain text, no icons)
            variant: Button variant ('primary', 'secondary', or 'stop')
            size: Button size ('sm', 'md', 'lg')
            full_width: Whether button should span full width

        Returns:
            Gradio Button component
        """
        scale = 0 if not full_width else 1

        return gr.Button(
            label,
            variant=variant,
            size=size,
            scale=scale
        )

    @staticmethod
    def create_copy_button(target_component) -> gr.Button:
        """
        Create a copy-to-clipboard button for a text component.

        Args:
            target_component: The Gradio component to copy from

        Returns:
            Gradio Button configured for copying
        """
        return gr.Button(
            "Copy",
            size="sm",
            variant="secondary",
            scale=0
        )

    @staticmethod
    def create_status_display(initial_message: str = "") -> gr.Markdown:
        """
        Create a Markdown component for displaying status messages.

        Args:
            initial_message: Initial message to display

        Returns:
            Gradio Markdown component configured for status display
        """
        return gr.Markdown(
            value=initial_message or StatusMessages.info(
                "Ready",
                "Waiting for input..."
            )
        )


# Common input placeholders for consistency
class Placeholders:
    """Standard placeholder text for common input types."""

    SESSION_ID = "e.g., session_001 or my_campaign_2024_10_25"
    CAMPAIGN_NAME = "e.g., Curse of Strahd or My Custom Campaign"
    CHARACTER_NAME = "e.g., Thorin Ironforge"
    PLAYER_NAME = "e.g., Alice B."
    NPC_NAME = "e.g., Strahd von Zarovich"
    LOCATION_NAME = "e.g., Castle Ravenloft"
    QUEST_NAME = "e.g., Find the Holy Symbol of Ravenkind"
    SEARCH_QUERY = "Search..."
    FILE_PATH = "Select a file or enter path..."
    API_KEY = "Enter your API key (optional)"
    MODEL_NAME = "e.g., gpt-4 or llama2"
    CONVERSATION_TITLE = "Untitled Conversation"
    CAMPAIGN_QUESTION = "e.g., What happened in session 5? Who is the Shadow Lord?"
    SESSION_NOTES = "Paste session notes here (Markdown supported)."
    PARTY_ID = "e.g., my_campaign_party"


# Common info/helper text
class InfoText:
    """Standard info/helper text for common components."""

    SESSION_ID = "A unique identifier for this session (alphanumeric, underscores, hyphens)"
    AUDIO_FILE = "Supported formats: M4A, WAV, MP3, FLAC (max 4GB)"
    CAMPAIGN_SELECT = "Choose which campaign this session belongs to"
    TRANSCRIPT_OUTPUT = "Processed transcript will appear here"
    PROCESSING_TIME = "Processing time varies: ~30-60 min for 4-hour session"
    API_KEY_OPTIONAL = "Leave blank to use default configuration"
    LLM_BACKEND = "Choose between local (Ollama) or cloud (OpenAI) processing"
    SESSION_NOTES = "Provide detailed session notes (Markdown supported)."