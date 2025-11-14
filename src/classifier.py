"""In-Character / Out-of-Character classification using LLM"""
import os
import re
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
from pathlib import Path
from .config import Config
from .logger import get_logger
from .preflight import PreflightIssue
from .retry import retry_with_backoff
from .constants import Classification, ConfidenceDefaults
from .rate_limiter import RateLimiter
from .llm_factory import OllamaClientFactory, OllamaConfig, OllamaConnectionError

try:  # Optional dependency for cloud inference
    from groq import Groq  # type: ignore
except Exception:  # pragma: no cover - optional import
    Groq = None


@dataclass
class ClassificationResult:
    """Result of IC/OOC classification for a segment"""
    segment_index: int
    classification: Classification  # Classification enum (IC, OOC, or MIXED)
    confidence: float  # 0.0 to 1.0
    reasoning: str
    character: Optional[str] = None  # Character name if IC

    def to_dict(self) -> dict:
        """Converts the ClassificationResult to a dictionary for serialization."""
        return {
            "segment_index": self.segment_index,
            "classification": self.classification.value,  # Serialize as string
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "character": self.character,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClassificationResult":
        """Creates a ClassificationResult from a dictionary."""
        return cls(
            segment_index=data["segment_index"],
            classification=Classification(data["classification"]),  # Parse from string
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

    def _build_prompt(
        self,
        prev_text: str,
        current_text: str,
        next_text: str,
        character_names: List[str],
        player_names: List[str]
    ) -> str:
        """
        Build classification prompt from the template.

        This default implementation uses the prompt_template attribute
        with placeholders for char_list, player_list, prev_text,
        current_text, and next_text.

        Subclasses can override this method to customize prompt building.

        Args:
            prev_text: Text from previous segment
            current_text: Text from current segment to classify
            next_text: Text from next segment
            character_names: List of character names
            player_names: List of player names

        Returns:
            Formatted prompt string ready for LLM
        """
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
        """
        Parse LLM response into ClassificationResult.

        This default implementation parses responses in the format:
        - Classificatie: IC|OOC|MIXED
        - Reden: <reasoning text>
        - Vertrouwen: <confidence value 0.0-1.0>
        - Personage: <character name or N/A>

        The field names are language-specific (Dutch by default).
        Subclasses can override this method to support different formats
        or languages.

        Args:
            response: Raw response text from LLM
            index: Segment index for logging purposes

        Returns:
            ClassificationResult with parsed values
        """
        classification = Classification.IN_CHARACTER
        confidence = ConfidenceDefaults.DEFAULT
        reasoning = "Could not parse response"
        character = None

        # Use regex to extract fields more robustly
        # This handles multi-line values and out-of-order fields
        import re

        # Extract classification
        class_match = re.search(r'Classificatie:\s*(\w+)', response, re.IGNORECASE)
        if class_match:
            class_text = class_match.group(1).strip().upper()
            try:
                classification = Classification(class_text)
            except ValueError:
                self.logger.warning(
                    "Invalid classification '%s' for segment %s, defaulting to IC",
                    class_text,
                    index
                )
                classification = Classification.IN_CHARACTER

        # Extract reasoning - capture everything after "Reden:" until next field or end
        reden_match = re.search(
            r'Reden:\s*(.+?)(?=(?:Vertrouwen:|Personage:|$))',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if reden_match:
            reasoning = reden_match.group(1).strip()

        # Extract confidence
        conf_match = re.search(r'Vertrouwen:\s*([\d.]+)', response, re.IGNORECASE)
        if conf_match:
            try:
                conf_text = conf_match.group(1).strip()
                confidence = float(conf_text)
                confidence = ConfidenceDefaults.clamp(confidence)
            except ValueError:
                self.logger.warning(
                    "Invalid confidence value '%s' for segment %s, using default.",
                    conf_text,
                    index
                )

        # Extract character name
        char_match = re.search(r'Personage:\s*(.+?)(?:\n|$)', response, re.IGNORECASE)
        if char_match:
            char_text = char_match.group(1).strip()
            if char_text.upper() != "N/A":
                character = char_text

        return ClassificationResult(
            segment_index=index,
            classification=classification,
            confidence=confidence,
            reasoning=reasoning,
            character=character
        )


class OllamaClassifier(BaseClassifier):
    """IC/OOC classifier using local Ollama LLM."""

    def __init__(
        self,
        model: str = None,
        base_url: str = None,
        fallback_model: Optional[str] = None
    ):
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

        # Initialize Ollama client using factory
        factory = OllamaClientFactory(logger=self.logger)
        ollama_config = OllamaConfig(
            host=self.base_url,
            timeout=30
        )

        try:
            self.client = factory.create_client(
                config=ollama_config,
                test_connection=True,
                max_retries=3,
                model_to_check=self.model  # Check model availability during connection test
            )

        except OllamaConnectionError as e:
            raise RuntimeError(
                f"Could not connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running.\n"
                f"Install: https://ollama.ai\n"
                f"Error: {e}"
            ) from e

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
                classification=Classification.IN_CHARACTER,
                confidence=ConfidenceDefaults.DEFAULT,
                reasoning="Classification failed, defaulted to IC"
            )

        return self._parse_response(response_text, index)

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


class GroqClassifier(BaseClassifier):
    """IC/OOC classifier using the Groq API."""

    def __init__(self, api_key: str = None, model: str = "llama-3.3-70b-versatile"):
        if Groq is None:
            raise ImportError("groq package is required for GroqClassifier.")
        self.api_key = api_key or Config.GROQ_API_KEY
        if not self.api_key:
            raise ValueError("Groq API key required. Set GROQ_API_KEY in .env")

        self.client = Groq(api_key=self.api_key)
        self.model = model
        self.logger = get_logger("classifier.groq")
        prompt_path = Config.PROJECT_ROOT / "src" / "prompts" / f"classifier_prompt_{Config.WHISPER_LANGUAGE}.txt"
        if not prompt_path.exists():
            self.logger.warning(f"Prompt file for language '{Config.WHISPER_LANGUAGE}' not found. Falling back to English.")
            prompt_path = Config.PROJECT_ROOT / "src" / "prompts" / "classifier_prompt_en.txt"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.prompt_template = f.read()
        except FileNotFoundError:
            raise RuntimeError(f"Prompt file not found at: {prompt_path}")

        self.rate_limiter = RateLimiter(
            max_calls=Config.GROQ_MAX_CALLS_PER_SECOND,
            period=Config.GROQ_RATE_LIMIT_PERIOD_SECONDS,
            burst_size=Config.GROQ_RATE_LIMIT_BURST,
        )

    def preflight_check(self):
        """Check that Groq API is accessible and configured."""
        issues = []

        if not self.api_key:
            issues.append(
                PreflightIssue(
                    component="classifier",
                    message="Groq API key not configured. Set GROQ_API_KEY in .env",
                    severity="error",
                )
            )
            return issues

        # Test API connectivity with a simple request
        try:
            test_response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": "test"}],
                model=self.model,
            )
        except Exception as exc:
            issues.append(
                PreflightIssue(
                    component="classifier",
                    message=f"Groq API test failed: {exc}",
                    severity="error",
                )
            )

        return issues

    def classify_segments(
        self,
        segments: List[Dict],
        character_names: List[str],
        player_names: List[str]
    ) -> List[ClassificationResult]:
        """Classify each segment using the Groq API."""
        results = []
        for i, segment in enumerate(segments):
            prev_text = segments[i-1]['text'] if i > 0 else ""
            current_text = segment['text']
            next_text = segments[i+1]['text'] if i < len(segments) - 1 else ""

            prompt = self._build_prompt(prev_text, current_text, next_text, character_names, player_names)

            try:
                response_text = self._make_api_call(prompt)
                results.append(self._parse_response(response_text, i))
            except Exception as e:
                self.logger.error(f"Error classifying segment {i} with Groq: {e}")
                results.append(ClassificationResult(
                    segment_index=i,
                    classification=Classification.IN_CHARACTER,
                    confidence=ConfidenceDefaults.DEFAULT,
                    reasoning="Classification failed, defaulted to IC"
                ))
        return results

    @retry_with_backoff()
    def _make_api_call(self, prompt):
        self.rate_limiter.acquire()
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
            )
        except Exception as exc:
            if self._is_rate_limit_error(exc):
                self.logger.warning(
                    "Groq rate limit exceeded (%s). Backing off for %.2fs.",
                    exc,
                    self.rate_limiter.period,
                )
                self.rate_limiter.penalize()
            raise
        return chat_completion.choices[0].message.content

    @staticmethod
    def _is_rate_limit_error(exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        if not status_code:
            response = getattr(exc, "response", None)
            if response:
                status_code = getattr(response, "status_code", None)

        if status_code == 429:
            return True
        message = str(exc).lower()
        return "rate_limit" in message or "429" in message


class ColabClassifier(BaseClassifier):
    """IC/OOC classifier using Google Colab via Google Drive file exchange."""

    def __init__(self, gdrive_mount_root: str = "/content/drive"):
        """
        Initialize Colab classifier with Google Drive integration.

        Args:
            gdrive_mount_root: Root path where Google Drive is mounted (for local testing,
                              use actual path like "G:/My Drive" on Windows)
        """
        self.logger = get_logger(__name__)
        self.gdrive_mount_root = Path(gdrive_mount_root)
        self.mydrive_dir = self._resolve_mydrive_dir()

        # Build full paths for pending and complete folders
        self.pending_dir = self.mydrive_dir / Config.GDRIVE_CLASSIFICATION_PENDING
        self.complete_dir = self.mydrive_dir / Config.GDRIVE_CLASSIFICATION_COMPLETE

        self.poll_interval = Config.COLAB_POLL_INTERVAL
        self.timeout = Config.COLAB_TIMEOUT

        # Use the default prompt template from Dutch classification
        self.prompt_template = """Context: D&D sessie in het Nederlands
Characters: {char_list}
Spelers: {player_list}

Analyseer dit segment en classificeer als IC (in-character), OOC (out-of-character), of MIXED:

Vorig segment: "{prev_text}"
Huidig segment: "{current_text}"
Volgend segment: "{next_text}"

Geef je antwoord in dit formaat:
Classificatie: IC|OOC|MIXED
Reden: <korte uitleg>
Vertrouwen: <0.0-1.0>
Personage: <naam of N/A>"""

    def _resolve_mydrive_dir(self) -> Path:
        """
        Resolve the Google Drive "My Drive" directory, handling OS differences.

        Returns:
            Path to the root of the user's "My Drive" directory
        """
        candidate_names = ("MyDrive", "My Drive")
        candidates = []
        if self.gdrive_mount_root.name in candidate_names:
            candidates.append(self.gdrive_mount_root)
        else:
            candidates.extend(self.gdrive_mount_root / name for name in candidate_names)
        candidates.append(self.gdrive_mount_root)

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return candidates[0]

    def preflight_check(self):
        """Check if Google Drive is accessible."""
        issues = []

        try:
            if not self.pending_dir.exists():
                issues.append(
                    PreflightIssue(
                        component="classifier",
                        message=f"Google Drive pending directory not found: {self.pending_dir}. "
                                "Please ensure Google Drive is mounted and folders exist.",
                        severity="error",
                    )
                )

            if not self.complete_dir.exists():
                issues.append(
                    PreflightIssue(
                        component="classifier",
                        message=f"Google Drive complete directory not found: {self.complete_dir}. "
                                "Please ensure Google Drive is mounted and folders exist.",
                        severity="error",
                    )
                )

        except Exception as exc:
            issues.append(
                PreflightIssue(
                    component="classifier",
                    message=f"Cannot access Google Drive: {exc}",
                    severity="error",
                )
            )

        return issues

    def classify_segments(
        self,
        segments: List[Dict],
        character_names: List[str],
        player_names: List[str]
    ) -> List[ClassificationResult]:
        """
        Classify segments by uploading to Google Drive and waiting for Colab to process.

        Args:
            segments: List of segment dictionaries with 'text' key
            character_names: List of character names
            player_names: List of player names

        Returns:
            List of ClassificationResult objects
        """
        import time
        import uuid

        # Generate unique job ID
        job_id = f"job_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        # Prepare job data
        job_data = {
            "job_id": job_id,
            "segments": segments,
            "character_names": character_names,
            "player_names": player_names,
            "prompt_template": self.prompt_template,
        }

        # Write job file to pending directory
        job_file = self.pending_dir / f"{job_id}.json"
        result_file = self.complete_dir / f"{job_id}_result.json"

        self.logger.info(f"Uploading classification job {job_id} to Google Drive...")

        try:
            with open(job_file, 'w', encoding='utf-8') as f:
                json.dump(job_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to write job file to Google Drive: {e}")
            raise RuntimeError(f"Could not write to Google Drive: {e}")

        # Poll for results
        self.logger.info(f"Waiting for Colab to process job {job_id}...")
        self.logger.info(f"Polling every {self.poll_interval}s for up to {self.timeout}s...")

        start_time = time.time()
        while True:
            elapsed = time.time() - start_time

            if elapsed > self.timeout:
                self.logger.error(f"Timeout waiting for Colab results after {elapsed:.1f}s")
                raise TimeoutError(
                    f"Colab classification timed out after {self.timeout}s. "
                    "Please ensure Colab notebook is running and processing jobs."
                )

            # Check if result file exists
            if result_file.exists():
                self.logger.info(f"Results ready after {elapsed:.1f}s")
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        result_data = json.load(f)

                    # Parse results
                    classifications = [
                        ClassificationResult.from_dict(c)
                        for c in result_data["classifications"]
                    ]

                    # Clean up files
                    try:
                        job_file.unlink()
                        result_file.unlink()
                    except Exception as cleanup_err:
                        self.logger.warning(f"Could not clean up job files: {cleanup_err}")

                    return classifications

                except Exception as e:
                    self.logger.error(f"Failed to parse result file: {e}")
                    raise RuntimeError(f"Could not parse Colab results: {e}")

            # Wait before next poll
            time.sleep(self.poll_interval)
            if int(elapsed) % 30 == 0:  # Log every 30s
                self.logger.info(f"Still waiting... ({elapsed:.0f}s elapsed)")


class ClassifierFactory:
    """Factory to create appropriate classifier."""

    @staticmethod
    def create(backend: str = None, gdrive_mount_root: str = None) -> BaseClassifier:
        """
        Create classifier instance.

        Args:
            backend: Backend type ('ollama', 'groq', 'colab', 'openai')
            gdrive_mount_root: For 'colab' backend, the Google Drive mount path
                              (defaults to "/content/drive" for Colab, or OS-specific for local)

        Returns:
            BaseClassifier instance
        """
        backend = backend or Config.LLM_BACKEND

        if backend == "ollama":
            return OllamaClassifier()
        elif backend == "groq":
            return GroqClassifier()
        elif backend == "colab":
            # Auto-detect Google Drive mount point if not specified
            if gdrive_mount_root is None:
                import platform
                if platform.system() == "Windows":
                    # Common Windows Google Drive paths
                    possible_paths = [
                        Path("G:/My Drive"),
                        Path(os.path.expanduser("~/Google Drive")),
                        Path("/content/drive"),  # For Colab itself
                    ]
                else:
                    # Unix/Linux/Mac
                    possible_paths = [
                        Path(os.path.expanduser("~/Google Drive")),
                        Path("/content/drive"),
                    ]

                # Find first existing path
                for path in possible_paths:
                    if path.exists():
                        gdrive_mount_root = str(path.parent if path.name == "My Drive" else path)
                        break
                else:
                    gdrive_mount_root = "/content/drive"  # Default to Colab path

            return ColabClassifier(gdrive_mount_root=gdrive_mount_root)
        elif backend == "openai":
            raise NotImplementedError("OpenAI classifier not yet implemented")
        else:
            raise ValueError(f"Unknown classifier backend: {backend}")
