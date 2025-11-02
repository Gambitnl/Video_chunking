"""High-level character profile extraction and update workflow."""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .character_profile import (
    CharacterProfile,
    CharacterProfileManager,
    ProfileUpdate,
)
from .party_config import Character, PartyConfigManager
from .profile_extractor import ProfileExtractor

LOGGER = logging.getLogger(__name__)


@dataclass
class ExtractedCharacterData:
    """Container for extracted character information from a session."""
    character_name: str
    notable_actions: List[str] = field(default_factory=list)
    items_acquired: List[str] = field(default_factory=list)
    relationships_mentioned: List[str] = field(default_factory=list)
    memorable_quotes: List[str] = field(default_factory=list)
    character_development: List[str] = field(default_factory=list)
    inventory_changes: List[str] = field(default_factory=list)
    goal_progress: List[str] = field(default_factory=list)
    background_revelations: List[str] = field(default_factory=list)


class CharacterProfileExtractor:
    """High-level workflow for extracting and updating character profiles from transcripts."""

    def __init__(self, profile_extractor: Optional[ProfileExtractor] = None):
        self.extractor = profile_extractor or ProfileExtractor()
        LOGGER.info("CharacterProfileExtractor initialized")

    def batch_extract_and_update(
        self,
        *,
        transcript_path: Path,
        party_id: str,
        session_id: str,
        profile_manager: CharacterProfileManager,
        party_manager: PartyConfigManager,
    ) -> Dict[str, ExtractedCharacterData]:
        """Extract character data from transcript and update profiles.

        Args:
            transcript_path: Path to IC-only transcript text file
            party_id: Party configuration ID
            session_id: Session identifier for tracking
            profile_manager: Manager for character profiles
            party_manager: Manager for party configurations

        Returns:
            Dictionary mapping character names to extracted data
        """
        LOGGER.info("Starting batch extraction for party '%s', session '%s'", party_id, session_id)

        party = party_manager.get_party(party_id)
        if not party:
            raise ValueError(f"Party configuration '{party_id}' not found")

        if not party.characters:
            raise ValueError(f"No characters defined in party '{party_id}'")

        character_lookup: Dict[str, Character] = {char.name: char for char in party.characters}
        character_names = list(character_lookup.keys())

        transcript_text = transcript_path.read_text(encoding="utf-8")
        transcript_segments = self._parse_transcript(transcript_text)
        if not transcript_segments:
            raise ValueError("Transcript file is empty or could not be parsed")

        LOGGER.info("Loaded %d transcript segments", len(transcript_segments))

        campaign_context_parts: List[str] = []
        if getattr(party, "campaign", None):
            campaign_context_parts.append(party.campaign)
        if getattr(party, "notes", None):
            campaign_context_parts.append(party.notes)
        campaign_context = " | ".join(filter(None, campaign_context_parts)) or "Unknown campaign"

        batch = self.extractor.extract_profile_updates(
            session_id=session_id,
            transcript_segments=transcript_segments,
            character_names=character_names,
            campaign_id=party_id,
            campaign_context=campaign_context,
        )

        LOGGER.info("Extracted %d profile updates", len(batch.updates))

        results: Dict[str, ExtractedCharacterData] = {
            name: ExtractedCharacterData(character_name=name) for name in character_names
        }
        updates_by_character: Dict[str, Dict[str, List[ProfileUpdate]]] = defaultdict(lambda: defaultdict(list))

        for update in batch.updates:
            resolved_name = self._resolve_character_name(
                update.character,
                party.characters,
                profile_manager,
            )
            if not resolved_name:
                LOGGER.warning("Skipping update for unknown character '%s'", update.character)
                continue

            update.character = resolved_name
            if not update.session_id:
                update.session_id = session_id

            extracted = results.setdefault(resolved_name, ExtractedCharacterData(character_name=resolved_name))
            self._accumulate_formatted_update(extracted, update)
            updates_by_character[resolved_name][update.category].append(update)

        for character_name, category_map in updates_by_character.items():
            self._ensure_profile(
                profile_manager,
                character_lookup.get(character_name),
                character_name,
                party,
                party_id,
            )
            profile_manager.merge_updates(character_name, category_map)

        updated_characters = {
            name: data for name, data in results.items() if self._has_updates(data)
        }
        LOGGER.info("Updated %d character profiles", len(updated_characters))
        return updated_characters

    def _parse_transcript(self, transcript_text: str) -> List[Dict[str, Any]]:
        """Parse transcript text into segments.

        Expected format:
        [00:12:34] Speaker 1: Dialogue text
        [01:23:45] Speaker 2: More dialogue
        """
        segments = []
        for line in transcript_text.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Try to parse [HH:MM:SS] or [MM:SS] format
            if line.startswith("["):
                try:
                    end_bracket = line.index("]")
                    timestamp_str = line[1:end_bracket]
                    rest = line[end_bracket + 1:].strip()

                    # Parse timestamp
                    parts = timestamp_str.split(":")
                    if len(parts) == 2:  # MM:SS
                        start_seconds = int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:  # HH:MM:SS
                        start_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    else:
                        start_seconds = 0.0

                    # Parse speaker and text
                    if ":" in rest:
                        speaker, text = rest.split(":", 1)
                        segments.append({
                            "text": text.strip(),
                            "speaker": speaker.strip(),
                            "start": float(start_seconds),
                            "end": float(start_seconds) + 5.0,  # Estimate 5 seconds per segment
                        })
                except (ValueError, IndexError):
                    # Couldn't parse, treat as plain text
                    segments.append({
                        "text": line,
                        "speaker": "Unknown",
                        "start": 0.0,
                        "end": 0.0,
                    })
            else:
                # Plain text line
                segments.append({
                    "text": line,
                    "speaker": "Unknown",
                    "start": 0.0,
                    "end": 0.0,
                })

        return segments

    def _format_action(self, update: ProfileUpdate) -> str:
        """Format a notable action update."""
        parts = [update.content]
        if update.context:
            parts.append(f"({update.context})")
        if update.timestamp:
            parts.append(f"[{update.timestamp}]")
        return " ".join(parts)

    def _format_quote(self, update: ProfileUpdate) -> str:
        """Format a memorable quote update."""
        quote = update.quote or update.content
        parts = [f'"{quote}"']
        if update.context:
            parts.append(f"- {update.context}")
        if update.timestamp:
            parts.append(f"[{update.timestamp}]")
        return " ".join(parts)

    def _format_development(self, update: ProfileUpdate) -> str:
        """Format a character development update."""
        parts = [update.content]
        if update.context:
            parts.append(f"- {update.context}")
        if update.timestamp:
            parts.append(f"[{update.timestamp}]")
        return " ".join(parts)

    def _format_relationship(self, update: ProfileUpdate) -> str:
        """Format a relationship update."""
        parts = [update.content]
        if update.type:
            parts.append(f"({update.type})")
        if update.context:
            parts.append(f"- {update.context}")
        if update.timestamp:
            parts.append(f"[{update.timestamp}]")
        return " ".join(parts)

    def _format_inventory(self, update: ProfileUpdate) -> str:
        """Format an inventory change update."""
        parts = [update.content]
        if update.context:
            parts.append(f"- {update.context}")
        if update.timestamp:
            parts.append(f"[{update.timestamp}]")
        return " ".join(parts)

    def _format_goal(self, update: ProfileUpdate) -> str:
        """Format a goal progress update."""
        parts = [update.content]
        if update.context:
            parts.append(f"- {update.context}")
        if update.timestamp:
            parts.append(f"[{update.timestamp}]")
        return " ".join(parts)

    def _accumulate_formatted_update(
        self,
        extracted: ExtractedCharacterData,
        update: ProfileUpdate,
    ) -> None:
        """Append a formatted update to the extracted data container."""
        category = update.category
        if category == "notable_actions":
            extracted.notable_actions.append(self._format_action(update))
        elif category == "memorable_quotes":
            extracted.memorable_quotes.append(self._format_quote(update))
        elif category == "development_notes":
            extracted.character_development.append(self._format_development(update))
        elif category == "relationships":
            extracted.relationships_mentioned.append(self._format_relationship(update))
        elif category == "inventory_changes":
            formatted = self._format_inventory(update)
            extracted.inventory_changes.append(formatted)
            extracted.items_acquired.append(formatted)
        elif category == "goal_progress":
            extracted.goal_progress.append(self._format_goal(update))
        elif category == "character_background":
            formatted = self._format_development(update)
            extracted.background_revelations.append(formatted)
            extracted.character_development.append(formatted)
        else:
            LOGGER.debug("Unhandled update category '%s' while formatting", category)

    def _resolve_character_name(
        self,
        raw_name: Optional[str],
        party_characters: List[Character],
        profile_manager: CharacterProfileManager,
    ) -> Optional[str]:
        """Find the canonical character name for an update."""
        if not raw_name:
            return None

        normalized = raw_name.strip().lower()
        for character in party_characters:
            if character.name.lower() == normalized:
                return character.name
            if character.aliases:
                for alias in character.aliases:
                    if alias.lower() == normalized:
                        return character.name

        for existing in profile_manager.list_characters():
            if existing.lower() == normalized:
                return existing

        return None

    def _ensure_profile(
        self,
        profile_manager: CharacterProfileManager,
        party_character: Optional[Character],
        character_name: str,
        party,
        campaign_id: str,
    ) -> CharacterProfile:
        """Ensure a CharacterProfile exists for the given character name."""
        profile = profile_manager.get_profile(character_name)
        if profile:
            return profile

        if party_character:
            profile = CharacterProfile(
                name=party_character.name,
                player=party_character.player or "Unknown Player",
                race=party_character.race or "",
                class_name=party_character.class_name or "",
                campaign_id=campaign_id,
                campaign_name=getattr(party, "campaign", "") or "",
                aliases=list(party_character.aliases or []),
            )
        else:
            profile = CharacterProfile(
                name=character_name,
                player="Unknown Player",
                race="",
                class_name="",
                campaign_id=campaign_id,
                campaign_name=getattr(party, "campaign", "") or "",
            )

        profile_manager.add_profile(character_name, profile)
        return profile

    def _has_updates(self, extracted: ExtractedCharacterData) -> bool:
        """Check if extracted data contains any updates."""
        return bool(
            extracted.notable_actions
            or extracted.items_acquired
            or extracted.relationships_mentioned
            or extracted.memorable_quotes
            or extracted.character_development
            or extracted.inventory_changes
            or extracted.goal_progress
            or extracted.background_revelations
        )

