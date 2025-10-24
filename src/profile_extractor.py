"""
Extracts character profile updates from transcripts.
"""
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path

from .config import Config
from .logger import get_logger
from .character_profile import CharacterProfile, ProfileUpdate, CharacterAction, CharacterItem, CharacterRelationship, CharacterDevelopment, CharacterQuote
from .party_config import PartyConfigManager

# Assuming an llm_client with a `generate` method is passed in.
# A more robust solution would define an abstract base class for the LLM client.


class ProfileExtractor:
    """Extracts character profile updates from transcripts."""

    def __init__(self, llm_client: Any = None, config: Config = None):
        from .llm_client import LlmClient
        self.config = config or Config()
        self.llm = llm_client or LlmClient(model=self.config.OLLAMA_MODEL, base_url=self.config.OLLAMA_BASE_URL)
        self.logger = get_logger("profile_extractor")
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        prompt_path = self.config.PROJECT_ROOT / "src" / "prompts" / "profile_extraction.txt"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            self.logger.error(f"Prompt file not found at: {prompt_path}")
            raise

    def _format_transcript_for_llm(self, transcript: List[Dict[str, Any]]) -> str:
        """Formats the transcript into a simple string for the LLM."""
        formatted_lines = []
        for segment in transcript:
            if segment.get('classification') == 'IC':
                formatted_lines.append(
                    f"[{segment['start_time']}] {segment['speaker']}: {segment['text']}"
                )
        return "\n".join(formatted_lines)

    def extract_moments(self, transcript: List[Dict[str, Any]]) -> List[ProfileUpdate]:
        """Extract character moments from transcript segments."""
        formatted_transcript = self._format_transcript_for_llm(transcript)
        if not formatted_transcript:
            self.logger.info("No IC segments found in the transcript. Skipping extraction.")
            return []

        prompt = self.prompt_template + "\n\nTranscript:\n" + formatted_transcript

        try:
            response = self.llm.generate(
                model=self.config.OLLAMA_MODEL, # Assuming Ollama for now
                prompt=prompt,
                options={
                    'temperature': 0.2,
                }
            )
            
            json_response = response['response']
            updates_data = json.loads(json_response)
            
            profile_updates = []
            for data in updates_data:
                profile_updates.append(ProfileUpdate(**data))
            
            return profile_updates

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from LLM response: {e}")
            self.logger.debug(f"LLM Response: {response.get('response', '')}")
            return []
        except Exception as e:
            self.logger.error(f"An error occurred during profile extraction: {e}")
            return []

    def suggest_updates(self, moments: List[ProfileUpdate], existing_profile: CharacterProfile) -> Dict[str, List[ProfileUpdate]]:
        """Generate suggested profile updates, filtering out duplicates."""
        suggestions = {
            "notable_actions": [],
            "inventory": [],
            "relationships": [],
            "development_notes": [],
            "memorable_quotes": [],
        }

        for moment in moments:
            if moment.character != existing_profile.name:
                continue

            category_map = {
                "Critical Actions": ("notable_actions", "description"),
                "Memorable Quotes": ("memorable_quotes", "quote"),
                "Character Development": ("development_notes", "note"),
                "Relationship Dynamics": ("relationships", "description"),
            }

            if moment.category in category_map:
                profile_attr, content_field = category_map[moment.category]
                
                # Basic deduplication based on content
                is_duplicate = False
                for existing_item in getattr(existing_profile, profile_attr):
                    if moment.content == getattr(existing_item, content_field):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    suggestions[profile_attr].append(moment)

        return suggestions

    def batch_extract_and_update(
        self,
        transcript_path: Path,
        party_id: str,
        session_id: str,
        profile_manager: Any, # CharacterProfileManager
        party_manager: PartyConfigManager,
    ) -> Dict[str, Any]:
        """Orchestrates the extraction and update process for a given party and session."""
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript = json.load(f)

        party = party_manager.get_party(party_id)
        if not party:
            raise ValueError(f"Party '{party_id}' not found.")

        all_moments = self.extract_moments(transcript)
        
        results = {}
        for character in party.characters:
            character_profile = profile_manager.get_profile(character.name)
            if not character_profile:
                self.logger.warning(f"Profile for character '{character.name}' not found. Skipping.")
                continue

            suggestions = self.suggest_updates(all_moments, character_profile)
            
            if any(suggestions.values()):
                self.logger.info(f"Found {sum(len(v) for v in suggestions.values())} new updates for {character.name}.")
                profile_manager.merge_updates(character.name, suggestions)
                results[character.name] = suggestions

        return results