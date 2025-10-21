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

    def _build_prompt(self, perspective_name: str, segments: List[Dict], character_names: List[str], narrator: bool, notebook_context: str) -> str:
        key_segments: List[str] = []
        for seg in segments:
            if seg.get("classification", "IC") != "IC":
                continue
            text = (seg.get("text") or "").strip()
            if not text:
                continue
            char = seg.get("character") or seg.get("speaker_name") or ""
            timestamp = seg.get("start_time")
            try:
                stamp = float(timestamp)
            except (TypeError, ValueError):
                stamp = 0.0
            key_segments.append(f"[{stamp:06.2f}] {char}: {text}")
            if len(key_segments) >= 60:
                break

        joined_segments = "\n".join(key_segments) if key_segments else "(Transcript excerpts unavailable)"
        persona = (
            f"You are the character {perspective_name}, one of the main protagonists."
            if not narrator
            else "You are an omniscient narrator summarizing events for the campaign log."
        )
        supporting = (
            "Campaign notebook excerpt:\n" + (notebook_context[:3000] if notebook_context else "(no additional notes provided)")
        )
        instructions = (
            "Write a concise per-session narrative (~3-5 paragraphs) capturing actions, emotions, and consequences. Maintain continuity with prior sessions and keep vocabulary consistent with the character's voice."
            if not narrator
            else "Provide a balanced overview highlighting each character's contributions while keeping the tone neutral and descriptive."
        )

        return (
            f"{persona}\n"
            "You are summarizing a D&D session using the following transcript extracts.\n"
            "Focus on the referenced events; infer light transitions when necessary but avoid inventing new story beats.\n"
            "Keep the output under 500 words.\n\n"
            "Transcript snippets:\n"
            f"{joined_segments}\n\n"
            f"{supporting}\n\n"
            "Instructions:\n"
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
