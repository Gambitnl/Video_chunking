"""In-Character / Out-of-Character classification using LLM"""
import os
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
from pathlib import Path
from .config import Config
from .logger import get_logger
from .preflight import PreflightIssue


@dataclass
class ClassificationResult:
    """Result of IC/OOC classification for a segment"""
    segment_index: int
    classification: str  # "IC", "OOC", or "MIXED"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    character: Optional[str] = None  # Character name if IC

    def to_dict(self) -> dict:
        """Converts the ClassificationResult to a dictionary for serialization."""
        return {
            "segment_index": self.segment_index,
            "classification": self.classification,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "character": self.character,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClassificationResult":
        """Creates a ClassificationResult from a dictionary."""
        return cls(
            segment_index=data["segment_index"],
            classification=data["classification"],
            confidence=data["confidence"],
            reasoning=data["reasoning"],
            character=data.get("character"),
        )


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

    def preflight_check(self):
        """Return an iterable of PreflightIssue objects."""
        return []


class OllamaClassifier(BaseClassifier):
    """IC/OOC classifier using local Ollama LLM."""

    def __init__(
        self,
        model: str = None,
        base_url: str = None,
        fallback_model: Optional[str] = None
    ):
        import ollama

        self.model = model or Config.OLLAMA_MODEL
        self.base_url = base_url or Config.OLLAMA_BASE_URL
        self.fallback_model = fallback_model or getattr(
            Config,
            "OLLAMA_FALLBACK_MODEL",
            None
        )
        self.logger = get_logger("classifier.ollama")

        # Load prompt template
        prompt_path = Config.PROJECT_ROOT / "src" / "prompts" / f"classifier_prompt_{Config.WHISPER_LANGUAGE}.txt"
        if not prompt_path.exists():
            self.logger.warning(f"Prompt file for language '{Config.WHISPER_LANGUAGE}' not found. Falling back to English.")
            prompt_path = Config.PROJECT_ROOT / "src" / "prompts" / "classifier_prompt_en.txt"
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

    def preflight_check(self):
        issues = []
        try:
            self.client.list()
        except Exception as exc:
            issues.append(
                PreflightIssue(
                    component="classifier",
                    message=f"Cannot reach Ollama at {self.base_url}: {exc}",
                    severity="error",
                )
            )
        memory_issue = self._memory_requirement_issue()
        if memory_issue:
            issues.append(memory_issue)
        return issues

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

        response_text = self._generate_with_retry(prompt, index)
        if response_text is None:
            return ClassificationResult(
                segment_index=index,
                classification="IC",
                confidence=0.5,
                reasoning="Classification failed, defaulted to IC"
            )

        return self._parse_response(response_text, index)

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

    def _generate_with_retry(self, prompt: str, index: int) -> Optional[str]:
        try:
            response = self._generate_with_model(self.model, prompt)
            return response['response']
        except Exception as exc:
            low_vram_response = self._maybe_retry_with_low_vram(prompt, index, exc)
            if low_vram_response is not None:
                return low_vram_response['response']

            fallback_response = self._maybe_retry_with_fallback(prompt, index, exc)
            if fallback_response is not None:
                return fallback_response['response']

            self.logger.warning(
                "Classification failed for segment %s using %s: %s",
                index,
                self.model,
                exc
            )
            return None

    def _generate_with_model(self, model: str, prompt: str, *, low_vram: bool = False):
        options = self._default_generation_options()
        if low_vram:
            options["low_vram"] = True
            if "num_ctx" in options:
                options["num_ctx"] = min(options["num_ctx"], 1024)
        return self.client.generate(
            model=model,
            prompt=prompt,
            options=options
        )

    def _default_generation_options(self) -> Dict[str, float]:
        return {
            'temperature': 0.1,
            'num_predict': 200,
            'num_ctx': 2048,
        }

    def _maybe_retry_with_low_vram(
        self,
        prompt: str,
        index: int,
        error: Exception
    ):
        if not self._is_memory_error(error):
            return None

        self.logger.warning(
            "Model %s hit a memory error on segment %s (%s). Retrying with low_vram settings.",
            self.model,
            index,
            error
        )

        try:
            return self._generate_with_model(self.model, prompt, low_vram=True)
        except Exception as low_vram_exc:
            self.logger.warning(
                "Low-VRAM retry also failed for segment %s: %s",
                index,
                low_vram_exc
            )
            return None

    def _maybe_retry_with_fallback(
        self,
        prompt: str,
        index: int,
        error: Exception
    ):
        fallback_model = self.fallback_model
        if not fallback_model or fallback_model == self.model:
            return None

        if not self._is_memory_error(error):
            return None

        self.logger.warning(
            "Model %s failed for segment %s (%s). Retrying with fallback %s. "
            "Update OLLAMA_MODEL or OLLAMA_FALLBACK_MODEL in your .env to avoid retries.",
            self.model,
            index,
            error,
            fallback_model
        )

        try:
            return self._generate_with_model(fallback_model, prompt)
        except Exception as fallback_exc:
            self.logger.warning(
                "Fallback model %s also failed for segment %s: %s. "
                "Update your Ollama model selection if the issue persists.",
                fallback_model,
                index,
                fallback_exc
            )
            return None

    def _is_memory_error(self, error: Exception) -> bool:
        message = str(error).lower()
        triggers = [
            "memory layout",
            "out of memory",
            "cuda out of memory",
            "not enough memory",
            "oom",
        ]
        return any(trigger in message for trigger in triggers)

    def _memory_requirement_issue(self) -> Optional[PreflightIssue]:
        required_gb = self._estimate_required_memory_gb(self.model)
        if required_gb is None:
            return None

        available_gb = self._estimate_total_memory_gb()
        if available_gb is None or available_gb >= required_gb:
            return None

        message = (
            f"Ollama model '{self.model}' typically needs ~{required_gb}GB RAM, "
            f"but only {available_gb:.1f}GB was detected. Expect memory layout "
            "errors unless you enable low_vram, reduce context, or choose a smaller model."
        )
        return PreflightIssue(
            component="classifier",
            message=message,
            severity="warning",
        )

    def _estimate_required_memory_gb(self, model_name: str) -> Optional[int]:
        model_lower = model_name.lower()
        match = re.search(r"(\d+)\s*b", model_lower)
        if not match:
            return None
        try:
            size = int(match.group(1))
        except (TypeError, ValueError):
            return None

        if size >= 20:
            return 16
        if size >= 14:
            return 12
        if size >= 10:
            return 10
        if size >= 7:
            return 8
        if size >= 5:
            return 6
        return None

    def _estimate_total_memory_gb(self) -> Optional[float]:
        bytes_per_gb = 1024 ** 3
        try:
            import psutil  # type: ignore

            return psutil.virtual_memory().total / bytes_per_gb
        except Exception:
            pass

        if hasattr(os, "sysconf"):
            try:
                page_size = os.sysconf("SC_PAGE_SIZE")
                phys_pages = os.sysconf("SC_PHYS_PAGES")
                if isinstance(page_size, int) and isinstance(phys_pages, int):
                    return (page_size * phys_pages) / bytes_per_gb
            except (ValueError, OSError, AttributeError):
                pass

        if os.name == "nt":
            try:
                import ctypes

                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_: List[tuple[str, Any]] = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                status = MEMORYSTATUSEX()
                status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                    return float(status.ullTotalPhys) / bytes_per_gb
            except Exception:
                pass

        return None

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
