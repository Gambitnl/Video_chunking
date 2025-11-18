"""
Data quality validation for character profiles.

Detects and reports data quality issues such as missing actions, duplicate items,
invalid session references, and inconsistencies across character profiles.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from collections import Counter
from datetime import datetime
import logging

from src.character_profile import CharacterProfileManager, CharacterProfile

logger = logging.getLogger(__name__)


@dataclass
class ValidationWarning:
    """
    Data quality warning.

    Represents a single data quality issue found during validation,
    with severity level and contextual information.
    """
    severity: str  # error, warning, info
    category: str  # missing_action, duplicate_item, invalid_session, etc.
    character: Optional[str] = None
    session: Optional[str] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate severity level on initialization."""
        valid_severities = ["error", "warning", "info"]
        if self.severity not in valid_severities:
            raise ValueError(f"Invalid severity '{self.severity}'. Must be one of: {valid_severities}")


@dataclass
class ValidationReport:
    """
    Complete validation report.

    Aggregates all validation warnings with summary statistics.
    """
    campaign_id: Optional[str] = None
    characters_validated: int = 0
    total_warnings: int = 0
    warnings: List[ValidationWarning] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)  # category -> count

    def __post_init__(self):
        """Calculate summary if warnings present."""
        if self.warnings and not self.summary:
            self.summary = Counter([w.category for w in self.warnings])
            self.total_warnings = len(self.warnings)


class DataValidator:
    """
    Data quality validation for character profiles.

    Validates character profile data for common issues and inconsistencies,
    generating detailed reports with actionable warnings.

    Example:
        ```python
        from src.analytics import DataValidator

        validator = DataValidator(profile_manager)

        # Validate single character
        warnings = validator.validate_character("Thorin")

        # Validate entire campaign
        report = validator.validate_campaign("crimson_company")

        # Generate report
        report_md = validator.generate_report(report.warnings)
        ```
    """

    def __init__(self, profile_manager: CharacterProfileManager):
        """
        Initialize data validator.

        Args:
            profile_manager: Character profile manager instance
        """
        self.profile_manager = profile_manager
        self.logger = logging.getLogger(__name__)

    def validate_character(
        self,
        character_name: str,
        known_sessions: Optional[List[str]] = None
    ) -> List[ValidationWarning]:
        """
        Validate single character profile.

        Checks for common data quality issues including missing data,
        duplicates, and invalid references.

        Args:
            character_name: Name of character to validate
            known_sessions: Optional list of valid session IDs for reference validation

        Returns:
            List of ValidationWarning objects

        Raises:
            ValueError: If character not found
        """
        profile = self.profile_manager.get_profile(character_name)
        if not profile:
            raise ValueError(f"Character '{character_name}' not found")

        warnings = []

        # Check for missing actions in sessions
        if known_sessions:
            warnings.extend(self.check_missing_actions(character_name, known_sessions))

        # Check for duplicate items
        warnings.extend(self.check_duplicate_items(character_name))

        # Check for relationships without first_met
        warnings.extend(self.check_missing_first_met(character_name))

        # Check for invalid timestamps
        warnings.extend(self.check_invalid_timestamps(character_name))

        # Check for empty/missing required fields
        warnings.extend(self.check_required_fields(character_name))

        return warnings

    def validate_campaign(
        self,
        campaign_id: Optional[str] = None
    ) -> ValidationReport:
        """
        Validate all characters in campaign.

        Runs validation on all characters and aggregates results into a report.

        Args:
            campaign_id: Campaign ID to validate. If None, validates all characters.

        Returns:
            ValidationReport with aggregated warnings

        Raises:
            ValueError: If campaign has no characters
        """
        # Get characters for campaign
        if campaign_id:
            profiles = self.profile_manager.get_profiles_by_campaign(campaign_id)
        else:
            profiles = self.profile_manager.profiles

        if not profiles:
            raise ValueError(f"No characters found for campaign '{campaign_id}'")

        # Collect all known sessions across the campaign
        all_sessions = set()
        for profile in profiles.values():
            all_sessions.update(profile.sessions_appeared)

        known_sessions = sorted(all_sessions)

        # Validate each character
        all_warnings = []
        for char_name in profiles.keys():
            char_warnings = self.validate_character(char_name, known_sessions)
            all_warnings.extend(char_warnings)

        # Create report
        report = ValidationReport(
            campaign_id=campaign_id,
            characters_validated=len(profiles),
            warnings=all_warnings
        )

        return report

    def check_missing_actions(
        self,
        character_name: str,
        known_sessions: List[str]
    ) -> List[ValidationWarning]:
        """
        Check for sessions with no actions recorded.

        Identifies sessions where character appeared but has no actions logged.

        Args:
            character_name: Name of character
            known_sessions: List of all valid session IDs

        Returns:
            List of ValidationWarning objects
        """
        profile = self.profile_manager.get_profile(character_name)
        if not profile:
            return []

        warnings = []

        # Get sessions with actions
        sessions_with_actions = set(action.session for action in profile.notable_actions)

        # Check each session character appeared in
        for session in profile.sessions_appeared:
            if session not in sessions_with_actions:
                warnings.append(ValidationWarning(
                    severity="warning",
                    category="missing_action",
                    character=character_name,
                    session=session,
                    message=f"Character appears in session_appeared list but has no actions recorded",
                    details={"session": session}
                ))

        return warnings

    def check_duplicate_items(
        self,
        character_name: str
    ) -> List[ValidationWarning]:
        """
        Check for duplicate inventory items.

        Identifies items acquired multiple times (potentially data entry errors).

        Args:
            character_name: Name of character

        Returns:
            List of ValidationWarning objects
        """
        profile = self.profile_manager.get_profile(character_name)
        if not profile:
            return []

        warnings = []

        # Count items by name + category
        item_occurrences = {}
        for item in profile.inventory:
            key = (item.name, item.category)
            item_occurrences.setdefault(key, []).append(item)

        # Find duplicates
        for (name, category), items in item_occurrences.items():
            if len(items) > 1:
                sessions = [item.session_acquired for item in items if item.session_acquired]
                warnings.append(ValidationWarning(
                    severity="warning",
                    category="duplicate_item",
                    character=character_name,
                    message=f"Item '{name}' acquired multiple times",
                    details={
                        "item_name": name,
                        "category": category,
                        "count": len(items),
                        "sessions": sessions
                    }
                ))

        return warnings

    def check_missing_first_met(
        self,
        character_name: str
    ) -> List[ValidationWarning]:
        """
        Check for relationships without first_met session.

        Identifies relationships missing the first_met field.

        Args:
            character_name: Name of character

        Returns:
            List of ValidationWarning objects
        """
        profile = self.profile_manager.get_profile(character_name)
        if not profile:
            return []

        warnings = []

        for rel in profile.relationships:
            if not rel.first_met:
                warnings.append(ValidationWarning(
                    severity="info",
                    category="missing_first_met",
                    character=character_name,
                    message=f"Relationship with '{rel.name}' has no first_met session",
                    details={
                        "relationship_name": rel.name,
                        "relationship_type": rel.relationship_type
                    }
                ))

        return warnings

    def check_invalid_timestamps(
        self,
        character_name: str
    ) -> List[ValidationWarning]:
        """
        Check for invalid timestamp formats.

        Identifies actions with malformed timestamp strings.

        Args:
            character_name: Name of character

        Returns:
            List of ValidationWarning objects
        """
        profile = self.profile_manager.get_profile(character_name)
        if not profile:
            return []

        warnings = []

        for action in profile.notable_actions:
            if action.timestamp and not self._is_valid_timestamp(action.timestamp):
                warnings.append(ValidationWarning(
                    severity="error",
                    category="invalid_timestamp",
                    character=character_name,
                    session=action.session,
                    message=f"Invalid timestamp format: '{action.timestamp}'",
                    details={
                        "timestamp": action.timestamp,
                        "description": action.description[:50]
                    }
                ))

        return warnings

    def _is_valid_timestamp(self, timestamp: str) -> bool:
        """
        Validate timestamp format (HH:MM:SS or MM:SS).

        Args:
            timestamp: Timestamp string to validate

        Returns:
            True if valid, False otherwise
        """
        if not timestamp:
            return True  # None/empty is acceptable

        parts = timestamp.split(":")
        if len(parts) not in (2, 3):
            return False

        try:
            # Check that all parts are valid integers
            for part in parts:
                int(part)
            return True
        except ValueError:
            return False

    def check_required_fields(
        self,
        character_name: str
    ) -> List[ValidationWarning]:
        """
        Check for missing required profile fields.

        Identifies empty or missing required fields like name, class, etc.

        Args:
            character_name: Name of character

        Returns:
            List of ValidationWarning objects
        """
        profile = self.profile_manager.get_profile(character_name)
        if not profile:
            return []

        warnings = []

        # Check required string fields
        required_fields = {
            "player": "Player name",
            "race": "Character race",
            "class_name": "Character class",
        }

        for field, display_name in required_fields.items():
            value = getattr(profile, field, None)
            if not value or not str(value).strip():
                warnings.append(ValidationWarning(
                    severity="warning",
                    category="missing_required_field",
                    character=character_name,
                    message=f"{display_name} is missing or empty",
                    details={"field": field}
                ))

        # Check level is positive
        if profile.level <= 0:
            warnings.append(ValidationWarning(
                severity="error",
                category="invalid_level",
                character=character_name,
                message=f"Character level is {profile.level} (must be positive)",
                details={"level": profile.level}
            ))

        return warnings

    def generate_report(
        self,
        warnings: List[ValidationWarning],
        campaign_id: Optional[str] = None
    ) -> str:
        """
        Generate markdown validation report.

        Creates a formatted report showing all warnings grouped by severity.

        Args:
            warnings: List of validation warnings
            campaign_id: Optional campaign ID for report title

        Returns:
            Markdown-formatted validation report
        """
        campaign_name = campaign_id or "All Characters"
        md = f"# Data Validation Report: {campaign_name}\n\n"
        md += f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        md += f"**Total Warnings**: {len(warnings)}\n\n"

        # Count by severity
        severity_counts = Counter([w.severity for w in warnings])

        md += "## Summary\n\n"
        for severity in ["error", "warning", "info"]:
            count = severity_counts.get(severity, 0)
            icon = {"error": "[ERROR]", "warning": "[WARNING]", "info": "[INFO]"}[severity]
            md += f"- {icon} **{severity.title()}**: {count}\n"
        md += "\n"

        # Group warnings by severity
        errors = [w for w in warnings if w.severity == "error"]
        warnings_list = [w for w in warnings if w.severity == "warning"]
        infos = [w for w in warnings if w.severity == "info"]

        # Display errors
        if errors:
            md += "## [ERROR] Errors\n\n"
            for warning in errors:
                md += self._format_warning(warning)
                md += "\n"

        # Display warnings
        if warnings_list:
            md += "## [WARNING] Warnings\n\n"
            for warning in warnings_list:
                md += self._format_warning(warning)
                md += "\n"

        # Display info
        if infos:
            md += "## [INFO] Information\n\n"
            for warning in infos:
                md += self._format_warning(warning)
                md += "\n"

        return md

    def _format_warning(self, warning: ValidationWarning) -> str:
        """
        Format a single warning for display.

        Args:
            warning: ValidationWarning to format

        Returns:
            Markdown-formatted warning
        """
        md = f"### [{warning.severity.upper()}] {warning.category.replace('_', ' ').title()}\n\n"

        if warning.character:
            md += f"**Character**: {warning.character}\n\n"

        if warning.session:
            md += f"**Session**: {warning.session}\n\n"

        md += f"**Message**: {warning.message}\n\n"

        if warning.details:
            md += "**Details**:\n"
            for key, value in warning.details.items():
                md += f"- {key}: {value}\n"
            md += "\n"

        md += "---\n\n"

        return md
