"""In-Character / Out-of-Character classification using LLM"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
from pathlib import Path
from .config import Config


@dataclass
class ClassificationResult:
    """Result of IC/OOC classification for a segment"""
    segment_index: int
    classification: str  # "IC", "OOC", or "MIXED"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    character: Optional[str] = None  # Character name if IC


class BaseClassifier(ABC):
    """Abstract base for IC/OOC classifiers"""

    @abstractmethod
    def classify_segments(
        self,
        segments: List[Dict],
        character_names: List[str],
        player_names: List[str]
    ) -> List[ClassificationResult]:
        """Classify segments as IC or OOC"""
        pass


class OllamaClassifier(BaseClassifier):
    """IC/OOC classifier using local Ollama LLM."""

    def __init__(self, model: str = None, base_url: str = None):
        import ollama

        self.model = model or Config.OLLAMA_MODEL
        self.base_url = base_url or Config.OLLAMA_BASE_URL

        # Load prompt template
        prompt_path = Config.PROJECT_ROOT / "src" / "prompts" / "classifier_prompt.txt"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.prompt_template = f.read()
        except FileNotFoundError:
            raise RuntimeError(f"Prompt file not found at: {prompt_path}")

        # Initialize client
        self.client = ollama.Client(host=self.base_url)

        # Test connection
        try:
            self.client.list()
        except Exception as e:
            raise RuntimeError(
                f"Could not connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running.\n"
                f"Install: https://ollama.ai\n"
                f"Error: {e}"
            )

    def classify_segments(
        self,
        segments: List[Dict],
        character_names: List[str],
        player_names: List[str]
    ) -> List[ClassificationResult]:
        """Classify each segment using LLM reasoning."""
        results = []

        for i, segment in enumerate(segments):
            prev_text = segments[i-1]['text'] if i > 0 else ""
            current_text = segment['text']
            next_text = segments[i+1]['text'] if i < len(segments) - 1 else ""

            result = self._classify_with_context(
                prev_text,
                current_text,
                next_text,
                character_names,
                player_names,
                i
            )
            results.append(result)

        return results

    def _classify_with_context(
        self,
        prev_text: str,
        current_text: str,
        next_text: str,
        character_names: List[str],
        player_names: List[str],
        index: int
    ) -> ClassificationResult:
        """Classify a single segment with context."""
        prompt = self._build_prompt(
            prev_text,
            current_text,
            next_text,
            character_names,
            player_names
        )

        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    'temperature': 0.1,
                    'num_predict': 200
                }
            )
            return self._parse_response(response['response'], index)
        except Exception as e:
            print(f"Warning: Classification failed for segment {index}: {e}")
            return ClassificationResult(
                segment_index=index,
                classification="IC",
                confidence=0.5,
                reasoning="Classification failed, defaulted to IC"
            )

    def _build_prompt(
        self,
        prev_text: str,
        current_text: str,
        next_text: str,
        character_names: List[str],
        player_names: List[str]
    ) -> str:
        """Build classification prompt from the template."""
        char_list = ", ".join(character_names) if character_names else "Unknown"
        player_list = ", ".join(player_names) if player_names else "Unknown"

        return self.prompt_template.format(
            char_list=char_list,
            player_list=player_list,
            prev_text=prev_text,
            current_text=current_text,
            next_text=next_text
        )

    def _parse_response(
        self,
        response: str,
        index: int
    ) -> ClassificationResult:
        """Parse LLM response into ClassificationResult."""
        classification = "IC"
        confidence = 0.5
        reasoning = "Could not parse response"
        character = None

        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("Classificatie:"):
                class_text = line.split(":", 1)[1].strip().upper()
                if class_text in ["IC", "OOC", "MIXED"]:
                    classification = class_text
            elif line.startswith("Reden:"):
                reasoning = line.split(":", 1)[1].strip()
            elif line.startswith("Vertrouwen:"):
                try:
                    conf_text = line.split(":", 1)[1].strip()
                    confidence = float(conf_text)
                    confidence = max(0.0, min(1.0, confidence))
                except ValueError:
                    pass
            elif line.startswith("Personage:"):
                char_text = line.split(":", 1)[1].strip()
                if char_text.upper() != "N/A":
                    character = char_text

        return ClassificationResult(
            segment_index=index,
            classification=classification,
            confidence=confidence,
            reasoning=reasoning,
            character=character
        )


class ClassifierFactory:
    """Factory to create appropriate classifier."""

    @staticmethod
    def create(backend: str = None) -> BaseClassifier:
        """Create classifier instance."""
        backend = backend or Config.LLM_BACKEND
        if backend == "ollama":
            return OllamaClassifier()
        elif backend == "openai":
            raise NotImplementedError("OpenAI classifier not yet implemented")
        else:
            raise ValueError(f"Unknown classifier backend: {backend}")