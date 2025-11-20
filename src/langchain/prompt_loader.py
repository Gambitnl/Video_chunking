"""
System prompt loading and campaign context management for LangChain chat.

This module provides utilities for loading and formatting system prompts
with campaign-specific context (campaign name, PC names, session counts).

Extracted from campaign_chat.py as part of BUG-20251102-07 refactoring.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("DDSessionProcessor.prompt_loader")


class SafeFormatDict(dict):
    """
    Dictionary that returns {key} for missing keys instead of raising KeyError.

    This allows template strings to gracefully handle missing placeholders
    by leaving them as-is (e.g., "{unknown_key}" remains "{unknown_key}").

    Example:
        >>> template = "Hello {name}, you have {count} messages"
        >>> context = SafeFormatDict(name="Alice")
        >>> template.format_map(context)
        'Hello Alice, you have {count} messages'
    """

    def __missing__(self, key: str) -> str:
        """Return placeholder string for missing keys."""
        return f"{{{key}}}"


class CampaignContextLoader:
    """
    Loads campaign-specific context data for prompt formatting.

    This class handles the complexity of loading campaign metadata from
    multiple manager classes (CampaignManager, PartyConfigManager,
    StoryNotebookManager) and provides a clean dictionary of context values.
    """

    def __init__(self, campaign_id: Optional[str] = None):
        """
        Initialize the context loader.

        Args:
            campaign_id: Optional campaign ID to load context for
        """
        self.campaign_id = campaign_id

    def load_context(self) -> Dict[str, any]:
        """
        Load campaign context data.

        Returns:
            Dictionary with keys:
                - campaign_name (str): Campaign name or "Unknown"
                - num_sessions (int): Number of sessions or 0
                - pc_names (str): Comma-separated PC names or "Unknown"

        Raises:
            No exceptions raised - returns default values on any error
        """
        # Default values when campaign_id is not provided or loading fails
        context = {
            "campaign_name": "Unknown",
            "num_sessions": 0,
            "pc_names": "Unknown",
        }

        if not self.campaign_id:
            return context

        try:
            # Import managers (may fail if dependencies not installed)
            from src.party_config import CampaignManager, PartyConfigManager
            from src.story_notebook import StoryNotebookManager

            # Load campaign info
            campaign_mgr = CampaignManager()
            campaign = campaign_mgr.get_campaign(self.campaign_id)

            if campaign:
                context["campaign_name"] = campaign.name

                # Load party info to get PC names
                if hasattr(campaign, 'party_id') and campaign.party_id:
                    party_mgr = PartyConfigManager()
                    party = party_mgr.get_party(campaign.party_id)

                    if party and hasattr(party, 'characters') and party.characters:
                        pc_names = [char.name for char in party.characters]
                        context["pc_names"] = ", ".join(pc_names)

                # Get session count for this campaign
                story_mgr = StoryNotebookManager()
                sessions = story_mgr.list_sessions(
                    limit=None,
                    campaign_id=self.campaign_id,
                    include_unassigned=False
                )
                context["num_sessions"] = len(sessions)

        except ImportError as e:
            logger.warning(
                f"Could not load campaign data for {self.campaign_id} "
                f"because a dependency is missing: {e}"
            )
        except Exception as e:
            logger.warning(
                f"Could not load campaign data for {self.campaign_id}: {e}",
                exc_info=True
            )

        return context


class SystemPromptLoader:
    """
    Loads and formats system prompt templates with campaign context.

    This class handles reading prompt template files from disk and formatting
    them with campaign-specific placeholder values.
    """

    DEFAULT_PROMPT = "You are a helpful D&D campaign assistant."

    def __init__(self, template_path: Optional[Path] = None):
        """
        Initialize the prompt loader.

        Args:
            template_path: Optional path to prompt template file.
                          Defaults to prompts/campaign_assistant.txt
        """
        if template_path is None:
            # Default path: src/langchain/ -> project_root/prompts/
            project_root = Path(__file__).parent.parent.parent
            template_path = project_root / "prompts" / "campaign_assistant.txt"

        self.template_path = template_path

    def load_template(self) -> str:
        """
        Load the prompt template from disk.

        Returns:
            Template string with {placeholder} markers

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template file not found: {self.template_path}")

        with open(self.template_path, "r", encoding="utf-8") as f:
            return f.read()

    def format_prompt(
        self,
        template: str,
        context: Dict[str, any]
    ) -> str:
        """
        Format a prompt template with context values.

        Args:
            template: Template string with {placeholder} markers
            context: Dictionary of placeholder values

        Returns:
            Formatted prompt string
        """
        safe_context = SafeFormatDict(**context)
        return template.format_map(safe_context)

    def load_and_format(
        self,
        campaign_id: Optional[str] = None
    ) -> str:
        """
        Load template and format with campaign context (convenience method).

        Args:
            campaign_id: Optional campaign ID to load context for

        Returns:
            Formatted system prompt string
        """
        try:
            # Load template
            template = self.load_template()

            # Load campaign context
            context_loader = CampaignContextLoader(campaign_id)
            context = context_loader.load_context()

            # Format and return
            return self.format_prompt(template, context)

        except FileNotFoundError:
            logger.warning(f"System prompt file not found: {self.template_path}")
            return self.DEFAULT_PROMPT
        except Exception as e:
            logger.error(f"Unexpected error loading prompt: {e}", exc_info=True)
            return self.DEFAULT_PROMPT
