"""Automatic character profile extraction from session transcripts using LLM"""
from pathlib import Path
from typing import List, Dict, Optional
import json
import logging
from dataclasses import dataclass, asdict


@dataclass
class ExtractedSessionData:
    """Data extracted from a single session for one character"""
    notable_actions: List[Dict]
    items_acquired: List[Dict]
    relationships_mentioned: List[Dict]
    memorable_quotes: List[Dict]
    character_development: List[Dict]


class CharacterProfileExtractor:
    """Extract character profile data from IC transcripts using LLM"""

    def __init__(self, ollama_model: str = "gpt-oss:20b", ollama_url: str = "http://localhost:11434"):
        """
        Initialize the profile extractor.

        Args:
            ollama_model: Ollama model to use for extraction
            ollama_url: Ollama server URL
        """
        self.logger = logging.getLogger(__name__)
        self.model = ollama_model
        self.ollama_url = ollama_url

        try:
            import ollama
            self.client = ollama.Client(host=ollama_url)
            self.logger.info(f"Initialized CharacterProfileExtractor with model: {ollama_model}")
        except ImportError:
            self.logger.error("Ollama package not installed. Install with: pip install ollama")
            raise
        except Exception as e:
            self.logger.warning(f"Could not connect to Ollama at {ollama_url}: {e}")
            self.client = None

    def extract_from_transcript(
        self,
        transcript_path: Path,
        character_names: List[str],
        session_id: str = None
    ) -> Dict[str, ExtractedSessionData]:
        """
        Extract character data from an IC-only transcript.

        Args:
            transcript_path: Path to IC-only transcript text file
            character_names: List of character names to extract data for
            session_id: Session identifier (e.g., "Session 1")

        Returns:
            Dictionary mapping character name to extracted data
        """
        self.logger.info(f"Extracting character data from: {transcript_path}")

        if not self.client:
            raise RuntimeError("Ollama client not initialized")

        # Read transcript
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript = f.read()

        if not transcript.strip():
            self.logger.warning(f"Transcript is empty: {transcript_path}")
            return {}

        results = {}
        for char_name in character_names:
            self.logger.info(f"Extracting data for character: {char_name}")
            try:
                extracted = self._extract_for_character(transcript, char_name, session_id)
                results[char_name] = extracted
            except Exception as e:
                self.logger.error(f"Failed to extract data for {char_name}: {e}", exc_info=True)
                # Return empty data on error
                results[char_name] = ExtractedSessionData(
                    notable_actions=[],
                    items_acquired=[],
                    relationships_mentioned=[],
                    memorable_quotes=[],
                    character_development=[]
                )

        return results

    def _extract_for_character(
        self,
        transcript: str,
        char_name: str,
        session_id: str = None
    ) -> ExtractedSessionData:
        """
        Use LLM to extract character-specific data from transcript.

        Args:
            transcript: Full IC-only transcript text
            char_name: Character name to extract data for
            session_id: Session identifier

        Returns:
            Extracted session data for the character
        """
        session_label = session_id or "Unknown Session"

        # Chunk transcript if too long (Ollama context limit ~4000 tokens)
        max_chars = 8000  # Conservative estimate
        transcript_chunk = transcript[:max_chars]
        if len(transcript) > max_chars:
            self.logger.warning(f"Transcript truncated from {len(transcript)} to {max_chars} chars")

        prompt = f"""Analyze this D&D session transcript and extract information about the character "{char_name}".

Return ONLY valid JSON in this exact format (no markdown, no extra text):
{{
    "notable_actions": [
        {{"description": "action description", "type": "combat|social|exploration|magic|divine", "timestamp": "HH:MM:SS or null"}}
    ],
    "items_acquired": [
        {{"name": "item name", "description": "item description", "category": "weapon|armor|magical|consumable|quest|equipment|misc"}}
    ],
    "relationships_mentioned": [
        {{"name": "NPC/character name", "relationship_type": "ally|enemy|neutral|mentor|friend|rival", "description": "relationship description"}}
    ],
    "memorable_quotes": [
        {{"quote": "exact quote", "context": "what was happening"}}
    ],
    "character_development": [
        {{"note": "development note", "category": "personality|goal|fear|trait|backstory"}}
    ]
}}

Rules:
- Only include information explicitly mentioned about {char_name}
- If no data for a category, return empty array []
- Use null for unknown timestamps
- Be conservative - only include clear, unambiguous information
- Return ONLY the JSON object, nothing else

Transcript:
{transcript_chunk}"""

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a D&D session analyzer. Extract structured character data and return ONLY valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                options={
                    "temperature": 0.3,  # Lower temperature for more consistent extraction
                    "num_predict": 2000
                }
            )

            # Parse response
            response_text = response['message']['content'].strip()

            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1])  # Remove first and last lines
                response_text = response_text.replace('```json', '').replace('```', '')

            data = json.loads(response_text)

            # Add session_id to all extracted items
            for action in data.get('notable_actions', []):
                action['session'] = session_label

            for quote in data.get('memorable_quotes', []):
                quote['session'] = session_label

            for dev in data.get('character_development', []):
                dev['session'] = session_label

            for item in data.get('items_acquired', []):
                if 'session_acquired' not in item:
                    item['session_acquired'] = session_label

            for rel in data.get('relationships_mentioned', []):
                if 'first_met' not in rel:
                    rel['first_met'] = session_label

            return ExtractedSessionData(**data)

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            self.logger.debug(f"Response was: {response_text}")
            raise ValueError(f"LLM returned invalid JSON: {e}")
        except Exception as e:
            self.logger.error(f"Extraction failed: {e}", exc_info=True)
            raise

    def update_character_profile(
        self,
        character_name: str,
        extracted_data: ExtractedSessionData,
        profile_manager
    ):
        """
        Update a character profile with extracted session data.

        Args:
            character_name: Name of character to update
            extracted_data: Data extracted from session
            profile_manager: CharacterProfileManager instance
        """
        from .character_profile import CharacterAction, CharacterItem, CharacterRelationship
        from .character_profile import CharacterDevelopment, CharacterQuote

        profile = profile_manager.get_profile(character_name)
        if not profile:
            self.logger.warning(f"Profile not found for {character_name}, skipping update")
            return

        # Add notable actions
        for action_dict in extracted_data.notable_actions:
            action = CharacterAction(**action_dict)
            profile.notable_actions.append(action)

        # Add items
        for item_dict in extracted_data.items_acquired:
            item = CharacterItem(**item_dict)
            profile.inventory.append(item)

        # Add relationships (avoid duplicates)
        existing_rels = {rel.name.lower() for rel in profile.relationships}
        for rel_dict in extracted_data.relationships_mentioned:
            if rel_dict['name'].lower() not in existing_rels:
                rel = CharacterRelationship(**rel_dict)
                profile.relationships.append(rel)

        # Add quotes
        for quote_dict in extracted_data.memorable_quotes:
            quote = CharacterQuote(**quote_dict)
            profile.memorable_quotes.append(quote)

        # Add development notes
        for dev_dict in extracted_data.character_development:
            dev = CharacterDevelopment(**dev_dict)
            profile.development_notes.append(dev)

        # Update session appearances if not already there
        session = extracted_data.notable_actions[0]['session'] if extracted_data.notable_actions else None
        if session and session not in profile.sessions_appeared:
            profile.sessions_appeared.append(session)
            profile.total_sessions = len(profile.sessions_appeared)

        # Save updated profile
        profile_manager.add_profile(character_name, profile)

        self.logger.info(
            f"Updated profile for {character_name}: "
            f"+{len(extracted_data.notable_actions)} actions, "
            f"+{len(extracted_data.items_acquired)} items, "
            f"+{len(extracted_data.relationships_mentioned)} relationships"
        )

    def batch_extract_and_update(
        self,
        transcript_path: Path,
        party_id: str,
        session_id: str,
        profile_manager,
        party_manager
    ) -> Dict[str, ExtractedSessionData]:
        """
        Extract data for all characters in a party and update their profiles.

        Args:
            transcript_path: Path to IC-only transcript
            party_id: Party configuration ID
            session_id: Session identifier
            profile_manager: CharacterProfileManager instance
            party_manager: PartyConfigManager instance

        Returns:
            Dictionary of extracted data per character
        """
        # Get character names from party config
        character_names = party_manager.get_character_names(party_id)

        if not character_names:
            self.logger.warning(f"No characters found in party '{party_id}'")
            return {}

        self.logger.info(f"Extracting data for {len(character_names)} characters from party '{party_id}'")

        # Extract data
        results = self.extract_from_transcript(transcript_path, character_names, session_id)

        # Update profiles
        for char_name, extracted_data in results.items():
            try:
                self.update_character_profile(char_name, extracted_data, profile_manager)
            except Exception as e:
                self.logger.error(f"Failed to update profile for {char_name}: {e}")

        return results
