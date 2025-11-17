"""High-level character profile extraction and update workflow."""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .character_profile import (
    CharacterProfile,
    CharacterProfileManager,
    ProfileUpdate,
)
from .diarizer import SpeakerProfileManager
from .party_config import Character, PartyConfigManager
from .profile_extractor import ProfileExtractor

LOGGER = logging.getLogger(__name__)
NAME_SPLIT_PATTERN = re.compile(r"\s*(?:,|&|/|\+|;|\band\b)\s*", re.IGNORECASE)


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
    """High-level workflow for extracting and updating character profiles from structured segments."""

    def __init__(self, profile_extractor: Optional[ProfileExtractor] = None):
        self.extractor = profile_extractor or ProfileExtractor()
        LOGGER.info("CharacterProfileExtractor initialized")

    def _extract_updates_from_segments(
        self,
        *,
        segments: List[Dict[str, Any]],
        party_id: str,
        session_id: str,
        character_names: List[str],
        campaign_context: str,
        campaign_id: Optional[str] = None,
    ) -> List[ProfileUpdate]:
        """Run profile extraction on a specific list of segments."""
        if not segments:
            return []

        batch = self.extractor.extract_profile_updates(
            session_id=session_id,
            transcript_segments=segments,
            character_names=character_names,
            campaign_id=campaign_id or party_id,
            campaign_context=campaign_context,
        )
        return batch.updates

    def extract_profiles_from_session(
        self,
        *,
        session_path: Path,
        party_id: str,
        session_id: str,
        profile_manager: CharacterProfileManager,
        party_manager: PartyConfigManager,
        campaign_id: Optional[str] = None,
    ) -> Dict[str, ExtractedCharacterData]:
        """
        Extracts character profiles from a session, processing scene-by-scene if available.
        """
        LOGGER.info("Starting profile extraction for party '%s', session '%s'", party_id, session_id)

        party = party_manager.get_party(party_id)
        if not party:
            raise ValueError(f"Party configuration '{party_id}' not found")

        character_lookup = {char.name: char for char in (party.characters or [])}
        character_names = list(character_lookup.keys())

        classification_file = session_path / "intermediates" / "stage_6_classification.json"
        scenes_file = session_path / "intermediates" / "stage_6_scenes.json"

        if not classification_file.exists():
            LOGGER.error(f"Classification file not found: {classification_file}")
            return {}

        with open(classification_file, 'r', encoding='utf-8') as f:
            all_segments = json.load(f)

        character_segments = [s for s in all_segments if s.get("classification_type") == "CHARACTER"]
        if not character_segments:
            LOGGER.info("No 'CHARACTER' type segments found. No profiles to update.")
            return {}
        
        LOGGER.info("Found %d 'CHARACTER' segments for profile extraction.", len(character_segments))

        base_campaign_context = " | ".join(filter(None, [getattr(party, "campaign", ""), getattr(party, "notes", "")])) or "Unknown campaign"
        
        all_updates: List[ProfileUpdate] = []

        if scenes_file.exists():
            LOGGER.info("Scenes file found, processing scene-by-scene.")
            with open(scenes_file, 'r', encoding='utf-8') as f:
                scenes = json.load(f)
            
            character_segments_by_id = {seg['segment_index']: seg for seg in character_segments}
            
            for i, scene in enumerate(scenes):
                scene_segment_ids = set(scene.get("segment_ids", []))
                scene_character_segments = [
                    character_segments_by_id[seg_id] 
                    for seg_id in scene_segment_ids 
                    if seg_id in character_segments_by_id
                ]
                
                if scene_character_segments:
                    # IMPROVEMENT: Add scene-level context to the prompt
                    dominant_type = scene.get("dominant_type", "UNKNOWN")
                    speakers = ", ".join(scene.get("speaker_list", []))
                    scene_context_str = f"Scene Context: This scene is primarily {dominant_type} and involves: {speakers}."
                    enriched_campaign_context = f"{scene_context_str}\n{base_campaign_context}"

                    LOGGER.info(f"Extracting profiles from scene {i+1}/{len(scenes)} with {len(scene_character_segments)} character segments.")
                    scene_updates = self._extract_updates_from_segments(
                        segments=scene_character_segments,
                        party_id=party_id,
                        session_id=session_id,
                        character_names=character_names,
                        campaign_context=enriched_campaign_context,
                        campaign_id=campaign_id,
                    )
                    all_updates.extend(scene_updates)
        else:
            LOGGER.info("No scenes file found, processing all character segments at once.")
            all_updates = self._extract_updates_from_segments(
                segments=character_segments,
                party_id=party_id,
                session_id=session_id,
                character_names=character_names,
                campaign_context=base_campaign_context,
                campaign_id=campaign_id,
            )

        LOGGER.info("Extracted a total of %d profile updates from LLM.", len(all_updates))
        if not all_updates:
            return {}

        # --- Merge all collected updates into profiles ---
        results: Dict[str, ExtractedCharacterData] = {
            name: ExtractedCharacterData(character_name=name) for name in character_names
        }
        updates_by_character: Dict[str, Dict[str, List[ProfileUpdate]]] = defaultdict(lambda: defaultdict(list))

        for update in all_updates:
            resolved_name = update.character
            if not resolved_name or resolved_name not in character_lookup:
                LOGGER.warning("Skipping update for unknown or unmapped character '%s'", update.character)
                continue

            update.session_id = update.session_id or session_id
            extracted = results.setdefault(resolved_name, ExtractedCharacterData(character_name=resolved_name))
            self._accumulate_formatted_update(extracted, update)
            updates_by_character[resolved_name][update.category].append(update)

        for character_name, category_map in updates_by_character.items():
            self._ensure_profile(
                profile_manager,
                character_lookup.get(character_name),
                character_name,
                party,
                campaign_id or party_id,
            )
            profile_manager.merge_updates(character_name, category_map)

        updated_characters = {
            name: data for name, data in results.items() if self._has_updates(data)
        }
        LOGGER.info("Updated %d character profiles.", len(updated_characters))
        return updated_characters

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

    def _ensure_profile(
        self,
        profile_manager: CharacterProfileManager,
        party_character: Optional[Character],
        character_name: str,
        party: Any,
        campaign_id: str,
    ) -> CharacterProfile:
        """Ensure a CharacterProfile exists for the given character name."""
        profile = profile_manager.get_profile(character_name)
        if profile:
            profile.campaign_id = campaign_id
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

    def batch_extract_and_update(
        self,
        *,
        transcript_path: Path,
        party_id: str,
        session_id: str,
        profile_manager: CharacterProfileManager,
        party_manager: PartyConfigManager,
        campaign_id: Optional[str] = None,
    ) -> Dict[str, ExtractedCharacterData]:
        """
        Extract character profile updates directly from a plaintext transcript.

        This is the workflow used by the Gradio Characters tab when a user uploads
        an IC-only transcript and expects character profiles to be updated.
        """
        if not transcript_path:
            raise ValueError("transcript_path is required for profile extraction.")
        if not transcript_path.exists():
            raise FileNotFoundError(f"Transcript file not found: {transcript_path}")

        party = party_manager.get_party(party_id)
        if not party:
            raise ValueError(f"Party configuration '{party_id}' not found")
        if not party.characters:
            raise ValueError(f"Party '{party_id}' does not have any characters configured.")

        segments = self._parse_plaintext_transcript(transcript_path)
        if not segments:
            LOGGER.warning("Transcript %s did not contain any usable segments.", transcript_path)
            return {}

        character_lookup = {char.name: char for char in party.characters}
        campaign_context = " | ".join(
            filter(None, [getattr(party, "campaign", "") or "", getattr(party, "notes", "") or ""])
        ) or "Unknown campaign"

        batch = self.extractor.extract_profile_updates(
            session_id=session_id,
            transcript_segments=segments,
            character_names=list(character_lookup.keys()),
            campaign_id=campaign_id or party_id,
            campaign_context=campaign_context,
            metadata={"source": "characters_tab_upload"},
        )

        updates = batch.updates or []
        if not updates:
            LOGGER.info(
                "Profile extraction returned no updates for session '%s' using transcript '%s'.",
                session_id,
                transcript_path,
            )
            return {}

        results: Dict[str, ExtractedCharacterData] = {}
        updates_by_character: Dict[str, Dict[str, List[ProfileUpdate]]] = defaultdict(lambda: defaultdict(list))

        for update in updates:
            resolved_name = self._resolve_character_name(update.character, character_lookup)
            if not resolved_name:
                LOGGER.warning("Skipping update for unknown or unmapped character '%s'", update.character)
                continue

            update.session_id = update.session_id or session_id
            extracted = results.setdefault(resolved_name, ExtractedCharacterData(character_name=resolved_name))
            self._accumulate_formatted_update(extracted, update)
            updates_by_character[resolved_name][update.category].append(update)

        for character_name, category_map in updates_by_character.items():
            self._ensure_profile(
                profile_manager,
                character_lookup.get(character_name),
                character_name,
                party,
                campaign_id or party_id,
            )
            profile_manager.merge_updates(character_name, category_map)

        updated_characters = {
            name: data for name, data in results.items() if self._has_updates(data)
        }
        LOGGER.info(
            "Updated %d character profiles via transcript upload workflow.",
            len(updated_characters),
        )
        return updated_characters

    def _parse_plaintext_transcript(self, transcript_path: Path) -> List[Dict[str, Any]]:
        """Convert a plaintext transcript into structured segments for extraction."""
        segments: List[Dict[str, Any]] = []
        with open(transcript_path, 'r', encoding='utf-8') as handle:
            for idx, raw_line in enumerate(handle):
                line = raw_line.strip()
                if not line:
                    continue

                timestamp = None
                speaker = "Unknown"
                text = line

                if line.startswith("[") and "]" in line:
                    closing = line.find("]")
                    ts_raw = line[1:closing].strip()
                    timestamp = self._timestamp_to_seconds(ts_raw)
                    text = line[closing + 1 :].strip()

                if ":" in text:
                    speaker_part, message = text.split(":", 1)
                    if speaker_part.strip():
                        speaker = speaker_part.strip()
                    text = message.strip()

                segments.append(
                    {
                        "segment_index": idx,
                        "speaker": speaker or "Unknown",
                        "text": text,
                        "start": timestamp if timestamp is not None else float(idx),
                    }
                )

        return segments

    def _timestamp_to_seconds(self, raw_value: Optional[str]) -> Optional[float]:
        """Convert HH:MM:SS or MM:SS strings into seconds."""
        if not raw_value:
            return None

        value = raw_value.strip()
        if not value:
            return None

        try:
            parts = value.split(":")
            if len(parts) == 3:
                hours, minutes, seconds = parts
                total = (int(hours) * 3600) + (int(minutes) * 60) + float(seconds)
                return float(total)
            if len(parts) == 2:
                minutes, seconds = parts
                return float((int(minutes) * 60) + float(seconds))
            return float(value)
        except ValueError:
            return None

    def _resolve_character_name(
        self,
        candidate: Optional[str],
        character_lookup: Dict[str, Character],
    ) -> Optional[str]:
        """Resolve a possibly aliased character name to the canonical party character."""
        if not candidate:
            return None

        normalized = candidate.strip().lower()
        if not normalized:
            return None

        for canonical_name, character in character_lookup.items():
            if normalized == canonical_name.lower():
                return canonical_name

            aliases = character.aliases or []
            if any(normalized == alias.lower() for alias in aliases):
                return canonical_name

        return None

