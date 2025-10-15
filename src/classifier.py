"""In-Character / Out-of-Character classification using LLM"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
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
    """
    IC/OOC classifier using local Ollama LLM.

    Strategy:
    - Use context window (previous/current/next segments)
    - Provide character and player names as reference
    - Ask for structured output (classification + confidence + reasoning)
    - Use few-shot examples for better accuracy

    Why Ollama:
    - Free, local, no API costs
    - Good Dutch language support (Llama 3.1)
    - Fast enough for post-processing
    """

    def __init__(self, model: str = None, base_url: str = None):
        import ollama

        self.model = model or Config.OLLAMA_MODEL
        self.base_url = base_url or Config.OLLAMA_BASE_URL

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
        """
        Classify each segment using LLM reasoning.

        Uses context window approach:
        - Looks at previous, current, and next segment
        - Provides better accuracy than isolated classification
        """
        results = []

        for i, segment in enumerate(segments):
            # Get context
            prev_text = segments[i-1]['text'] if i > 0 else ""
            current_text = segment['text']
            next_text = segments[i+1]['text'] if i < len(segments) - 1 else ""

            # Classify with context
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
        """Classify a single segment with context"""

        prompt = self._build_prompt(
            prev_text,
            current_text,
            next_text,
            character_names,
            player_names
        )

        try:
            # Call Ollama
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    'temperature': 0.1,  # Low temperature for consistent classification
                    'num_predict': 200
                }
            )

            # Parse response
            return self._parse_response(response['response'], index)

        except Exception as e:
            print(f"Warning: Classification failed for segment {index}: {e}")
            # Fallback to IC classification
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
        """
        Build classification prompt with few-shot examples.

        Design:
        - Clear task definition
        - Few-shot examples in Dutch
        - Context window
        - Structured output format
        """
        char_list = ", ".join(character_names) if character_names else "Unknown"
        player_list = ", ".join(player_names) if player_names else "Unknown"

        prompt = f"""Je bent een expert in het analyseren van Dungeons & Dragons sessies in het Nederlands.

Taak: Classificeer of een uitspraak "In-Character" (IC) of "Out-of-Character" (OOC) is.

- IC = De speler praat als hun personage, of de DM beschrijft de wereld/speelt een NPC
- OOC = Spelers praten over spelregels, maken grappen over het spel, of hebben real-life gesprekken

Personages: {char_list}
Spelers: {player_list}

Voorbeelden:

Vorige: "De goblin valt aan met zijn zwaard."
Huidige: "Ik rol voor initiatief."
Volgende: "Dat is een 15."
Classificatie: OOC
Reden: Praat over spelregels (initiatiefrol)
Vertrouwen: 0.95

Vorige: "Wat zie ik in de kamer?"
Huidige: "Je ziet een oude houten tafel met een kaars erop."
Volgende: "Ik loop naar de tafel toe."
Classificatie: IC
Reden: DM beschrijft de scène
Vertrouwen: 0.98

Vorige: "Iemand nog koffie?"
Huidige: "Ja graag!"
Volgende: "Ik pak de pot even."
Classificatie: OOC
Reden: Real-life gesprek over koffie
Vertrouwen: 0.99

Nu jouw beurt:

Vorige: "{prev_text}"
Huidige: "{current_text}"
Volgende: "{next_text}"

Geef je antwoord in exact dit formaat:
Classificatie: [IC/OOC/MIXED]
Reden: [korte uitleg]
Vertrouwen: [0.0-1.0]
Personage: [naam of N/A]
"""

        return prompt

    def _parse_response(
        self,
        response: str,
        index: int
    ) -> ClassificationResult:
        """Parse LLM response into ClassificationResult"""

        # Default values
        classification = "IC"
        confidence = 0.5
        reasoning = "Could not parse response"
        character = None

        # Parse response
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
                    confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
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
    """Factory to create appropriate classifier"""

    @staticmethod
    def create(backend: str = None) -> BaseClassifier:
        """
        Create classifier instance.

        Args:
            backend: 'ollama' or 'openai' (defaults to config)

        Returns:
            Appropriate classifier instance
        """
        backend = backend or Config.LLM_BACKEND

        if backend == "ollama":
            return OllamaClassifier()
        elif backend == "openai":
            # TODO: Implement OpenAI classifier if needed
            raise NotImplementedError("OpenAI classifier not yet implemented")
        else:
            raise ValueError(f"Unknown classifier backend: {backend}")
