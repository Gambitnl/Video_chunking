"""Migration utilities for adding campaign support to existing data."""
import json
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime

from .config import Config
from .logger import get_logger
from .party_config import CampaignManager
from .character_profile import CharacterProfileManager


@dataclass
class MigrationReport:
    """Report of migration actions taken."""
    sessions_migrated: int = 0
    sessions_skipped: int = 0
    profiles_migrated: int = 0
    profiles_skipped: int = 0
    narratives_migrated: int = 0
    narratives_skipped: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class CampaignMigration:
    """Utilities for migrating existing data to campaign-aware schema."""

    def __init__(self):
        self.logger = get_logger('campaign_migration')
        self.campaign_manager = CampaignManager()

    def migrate_session_metadata(
        self,
        campaign_id: str,
        dry_run: bool = False,
        session_filter: Optional[str] = None
    ) -> MigrationReport:
        """
        Add campaign_id to existing session metadata files.

        Args:
            campaign_id: Campaign identifier to assign to sessions
            dry_run: If True, don't actually modify files
            session_filter: Optional glob pattern to filter sessions (e.g., "Session_*")

        Returns:
            MigrationReport with results
        """
        report = MigrationReport()
        output_dir = Config.OUTPUT_DIR

        if not output_dir.exists():
            self.logger.warning(f"Output directory does not exist: {output_dir}")
            return report

        # Verify campaign exists
        campaign = self.campaign_manager.get_campaign(campaign_id)
        if not campaign:
            error_msg = f"Campaign '{campaign_id}' not found"
            self.logger.error(error_msg)
            report.errors.append(error_msg)
            return report

        campaign_name = campaign.name
        self.logger.info(
            f"{'[DRY RUN] ' if dry_run else ''}Migrating sessions to campaign: {campaign_name} ({campaign_id})"
        )

        # Find all session directories
        skip_dirs = {"_checkpoints", "segments", "imported_narratives"}

        for session_dir in output_dir.iterdir():
            if not session_dir.is_dir() or session_dir.name in skip_dirs:
                continue

            # Apply filter if specified
            if session_filter and not self._matches_pattern(session_dir.name, session_filter):
                continue

            # Find *_data.json file
            data_files = list(session_dir.glob("*_data.json"))
            if not data_files:
                self.logger.debug(f"No data file found in {session_dir.name}, skipping")
                report.sessions_skipped += 1
                continue

            data_file = data_files[0]

            try:
                # Load existing metadata
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                metadata = data.get('metadata', {})

                # Check if already migrated
                if metadata.get('campaign_id') is not None:
                    self.logger.debug(f"Session {session_dir.name} already has campaign_id, skipping")
                    report.sessions_skipped += 1
                    continue

                # Add campaign metadata
                metadata['campaign_id'] = campaign_id
                metadata['campaign_name'] = campaign_name
                if 'party_id' not in metadata:
                    metadata['party_id'] = campaign.party_id

                data['metadata'] = metadata

                if dry_run:
                    self.logger.info(f"[DRY RUN] Would update {data_file.name} with campaign_id={campaign_id}")
                else:
                    # Write updated metadata
                    with open(data_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    self.logger.info(f"Updated {data_file.name} with campaign_id={campaign_id}")

                report.sessions_migrated += 1

            except Exception as e:
                error_msg = f"Error migrating {data_file}: {e}"
                self.logger.error(error_msg)
                report.errors.append(error_msg)

        return report

    def migrate_character_profiles(
        self,
        campaign_id: str,
        dry_run: bool = False,
        character_filter: Optional[List[str]] = None
    ) -> MigrationReport:
        """
        Assign campaign_id to existing character profiles.

        Args:
            campaign_id: Campaign identifier to assign
            dry_run: If True, don't actually save changes
            character_filter: Optional list of character names to migrate (None = all)

        Returns:
            MigrationReport with results
        """
        report = MigrationReport()

        # Verify campaign exists
        campaign = self.campaign_manager.get_campaign(campaign_id)
        if not campaign:
            error_msg = f"Campaign '{campaign_id}' not found"
            self.logger.error(error_msg)
            report.errors.append(error_msg)
            return report

        campaign_name = campaign.name
        self.logger.info(
            f"{'[DRY RUN] ' if dry_run else ''}Migrating character profiles to campaign: {campaign_name} ({campaign_id})"
        )

        # Load profiles
        profile_manager = CharacterProfileManager()

        for name, profile in profile_manager.profiles.items():
            # Apply filter if specified
            if character_filter and name not in character_filter:
                continue

            # Skip if already assigned to this campaign
            if profile.campaign_id == campaign_id:
                self.logger.debug(f"Profile '{name}' already assigned to {campaign_id}, skipping")
                report.profiles_skipped += 1
                continue

            # Skip if already assigned to a different campaign (don't override)
            if profile.campaign_id is not None:
                self.logger.warning(
                    f"Profile '{name}' already assigned to campaign '{profile.campaign_id}', skipping"
                )
                report.profiles_skipped += 1
                continue

            # Assign campaign
            profile.campaign_id = campaign_id
            if not profile.campaign_name:
                profile.campaign_name = campaign_name

            if dry_run:
                self.logger.info(f"[DRY RUN] Would assign '{name}' to campaign {campaign_id}")
            else:
                profile_manager._save_single_profile(profile)
                self.logger.info(f"Assigned '{name}' to campaign {campaign_id}")

            report.profiles_migrated += 1

        return report

    def migrate_narrative_frontmatter(
        self,
        campaign_id: str,
        dry_run: bool = False
    ) -> MigrationReport:
        """
        Add YAML frontmatter with campaign metadata to existing narrative files.

        Args:
            campaign_id: Campaign identifier to add
            dry_run: If True, don't actually modify files

        Returns:
            MigrationReport with results
        """
        report = MigrationReport()

        # Verify campaign exists
        campaign = self.campaign_manager.get_campaign(campaign_id)
        if not campaign:
            error_msg = f"Campaign '{campaign_id}' not found"
            self.logger.error(error_msg)
            report.errors.append(error_msg)
            return report

        campaign_name = campaign.name
        self.logger.info(
            f"{'[DRY RUN] ' if dry_run else ''}Adding frontmatter to narratives for campaign: {campaign_name}"
        )

        # Find all narrative markdown files
        narrative_paths = []

        # Check session narratives
        for session_dir in Config.OUTPUT_DIR.iterdir():
            if session_dir.is_dir() and session_dir.name not in {"_checkpoints", "segments"}:
                narratives_dir = session_dir / "narratives"
                if narratives_dir.exists():
                    narrative_paths.extend(narratives_dir.glob("*.md"))

        # Check imported narratives
        imported_dir = Config.OUTPUT_DIR / "imported_narratives"
        if imported_dir.exists():
            narrative_paths.extend(imported_dir.glob("*.md"))

        for narrative_file in narrative_paths:
            try:
                # Read existing content
                content = narrative_file.read_text(encoding='utf-8')

                # Check if already has frontmatter
                if content.startswith('---\n'):
                    self.logger.debug(f"{narrative_file.name} already has frontmatter, skipping")
                    report.narratives_skipped += 1
                    continue

                # Extract session_id from filename or content
                session_id = self._extract_session_id(narrative_file)

                # Create frontmatter
                frontmatter = self._create_narrative_frontmatter(
                    campaign_id=campaign_id,
                    campaign_name=campaign_name,
                    session_id=session_id
                )

                # Prepend frontmatter
                new_content = f"{frontmatter}\n{content}"

                if dry_run:
                    self.logger.info(f"[DRY RUN] Would add frontmatter to {narrative_file.name}")
                else:
                    narrative_file.write_text(new_content, encoding='utf-8')
                    self.logger.info(f"Added frontmatter to {narrative_file.name}")

                report.narratives_migrated += 1

            except Exception as e:
                error_msg = f"Error migrating {narrative_file.name}: {e}"
                self.logger.error(error_msg)
                report.errors.append(error_msg)

        return report

    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Simple glob pattern matching."""
        import fnmatch
        return fnmatch.fnmatch(text, pattern)

    def _extract_session_id(self, narrative_file: Path) -> Optional[str]:
        """Try to extract session_id from narrative file path or content."""
        # Try to get from parent directory name
        parent = narrative_file.parent
        if parent.name == "narratives":
            # Parent is session directory
            session_dir_name = parent.parent.name
            # Format: YYYYMMDD_HHMMSS_session_id
            parts = session_dir_name.split('_', 2)
            if len(parts) >= 3:
                return parts[2]

        # Try to extract from filename
        # Common patterns: "Session_01.md", "session_01_narrative.md"
        stem = narrative_file.stem
        if stem.startswith('Session_') or stem.startswith('session_'):
            return stem

        return None

    def _create_narrative_frontmatter(
        self,
        campaign_id: str,
        campaign_name: str,
        session_id: Optional[str]
    ) -> str:
        """Create YAML frontmatter for narrative files."""
        lines = ["---"]
        lines.append(f"campaign_id: {campaign_id}")
        lines.append(f"campaign_name: {campaign_name}")
        if session_id:
            lines.append(f"session_id: {session_id}")
        lines.append(f"migrated_at: {datetime.now().isoformat()}")
        lines.append("---")
        return "\n".join(lines)

    def generate_migration_report_markdown(
        self,
        sessions_report: Optional[MigrationReport] = None,
        profiles_report: Optional[MigrationReport] = None,
        narratives_report: Optional[MigrationReport] = None
    ) -> str:
        """Generate a markdown migration report."""
        lines = [
            "# Campaign Migration Report",
            f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]

        if sessions_report:
            lines.extend([
                "## Session Metadata",
                f"- **Migrated**: {sessions_report.sessions_migrated}",
                f"- **Skipped**: {sessions_report.sessions_skipped}",
                ""
            ])
            if sessions_report.errors:
                lines.append("**Errors:**")
                for error in sessions_report.errors:
                    lines.append(f"- {error}")
                lines.append("")

        if profiles_report:
            lines.extend([
                "## Character Profiles",
                f"- **Migrated**: {profiles_report.profiles_migrated}",
                f"- **Skipped**: {profiles_report.profiles_skipped}",
                ""
            ])
            if profiles_report.errors:
                lines.append("**Errors:**")
                for error in profiles_report.errors:
                    lines.append(f"- {error}")
                lines.append("")

        if narratives_report:
            lines.extend([
                "## Narrative Files",
                f"- **Migrated**: {narratives_report.narratives_migrated}",
                f"- **Skipped**: {narratives_report.narratives_skipped}",
                ""
            ])
            if narratives_report.errors:
                lines.append("**Errors:**")
                for error in narratives_report.errors:
                    lines.append(f"- {error}")
                lines.append("")

        return "\n".join(lines)
