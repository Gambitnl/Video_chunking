import sys
import io
import logging
from contextlib import contextmanager
from typing import List, Dict

import ollama

from .config import Config

class StoryGenerator:
    """Handles the generation of session narratives using an LLM."""

    def __init__(self):
        self.client = ollama.Client(host=Config.OLLAMA_BASE_URL)

    @contextmanager
    def suppress_llm_logs(self):
        """Temporarily suppress stdout/stderr and critical logs from ollama."""
        ollama_logger = logging.getLogger("ollama")
        original_level = ollama_logger.level
        ollama_logger.setLevel(logging.CRITICAL)

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            ollama_logger.setLevel(original_level)

    def _build_story_transcript(self, segments: List[Dict], perspective_name: str) -> str:
        """
        Build a rich, story-like transcript from structured segments.
        """
        story_parts: List[str] = []
        narrative_types = {"CHARACTER", "DM_NARRATION", "NPC_DIALOGUE"}

        for seg in segments:
            classification_type = seg.get("classification_type")
            if not classification_type in narrative_types:
                continue

            text = (seg.get("text") or "").strip()
            if not text:
                continue

            actor = seg.get("character_name") or seg.get("speaker_name", "Unknown")

            if classification_type == "DM_NARRATION":
                story_parts.append(text)
            elif classification_type in ("CHARACTER", "NPC_DIALOGUE"):
                pov_marker = ""
                if perspective_name.lower() == actor.lower():
                    pov_marker = " (You)"
                
                story_parts.append(f'{actor}{pov_marker}: "{text}"')
        
        return "\n\n".join(story_parts)


    def _build_prompt(self, perspective_name: str, segments: List[Dict], character_names: List[str], narrator: bool, notebook_context: str) -> str:
        
        story_transcript = self._build_story_transcript(segments, perspective_name)
        if not story_transcript:
            story_transcript = "(No narrative segments were found in this session.)"

        persona = (
            f"You are the character {perspective_name}, one of the main protagonists."
            if not narrator
            else "You are an omniscient narrator summarizing events for the campaign log."
        )
        
        supporting = (
            "Campaign notebook excerpt:\n" + (notebook_context[:3000] if notebook_context else "(no additional notes provided)")
        )
        
        instructions = (
            f"Write a concise, first-person narrative from the perspective of {perspective_name} (~3-5 paragraphs) capturing your actions, emotions, and consequences. Maintain continuity with prior sessions and keep your vocabulary consistent with your character's voice."
            if not narrator
            else "Provide a balanced, third-person overview highlighting each character's contributions while keeping the tone neutral and descriptive. Write it in the style of a fantasy novel."
        )

        return (
            f"{persona}\n"
            "You are to write a story summary of a D&D session using the following story transcript.\n"
            "Focus on the referenced events; infer light transitions when necessary but avoid inventing new story beats.\n"
            "Keep the output under 500 words.\n\n"
            "**Story Transcript**:\n"
            f"{story_transcript}\n\n"
            f"**Supporting Notes**:\n{supporting}\n\n"
            "**Your Task**:\n"
            f"{instructions}\n"
        )

    def _generate_story(self, prompt: str, temperature: float = 0.5) -> str:
        with self.suppress_llm_logs():
            response = self.client.generate(
                model=Config.OLLAMA_MODEL,
                prompt=prompt,
                options={"temperature": temperature, "num_predict": 800},
            )
        return response.get("response", "(LLM returned no text)")

    def generate_narrator_summary(self, segments: List[Dict], character_names: List[str], notebook_context: str, temperature: float = 0.5) -> str:
        prompt = self._build_prompt("Narrator", segments, character_names, True, notebook_context)
        return self._generate_story(prompt, temperature)

    def generate_character_pov(self, segments: List[Dict], character_name: str, character_names: List[str], notebook_context: str, temperature: float = 0.5) -> str:
        prompt = self._build_prompt(character_name, segments, character_names, False, notebook_context)
        return self._generate_story(prompt, temperature)
