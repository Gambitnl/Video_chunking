"""In-Character / Out-of-Character classification using LLM"""
import hashlib
import os
import re
import json
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
from pathlib import Path
from .config import Config
from .logger import get_logger
from .preflight import PreflightIssue
from .retry import retry_with_backoff
from .constants import Classification, ClassificationType, ConfidenceDefaults
from .rate_limiter import RateLimiter
from .status_tracker import StatusTracker
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
    classification_type: ClassificationType = ClassificationType.UNKNOWN
    speaker_label: Optional[str] = None
    speaker_name: Optional[str] = None
    speaker_role: Optional[str] = None
    character_confidence: Optional[float] = None
    unknown_speaker: bool = False
    temporal_metadata: Optional[Dict[str, Any]] = None
    prompt_hash: Optional[str] = None
    response_hash: Optional[str] = None
    prompt_preview: Optional[str] = None
    response_preview: Optional[str] = None
    generation_latency_ms: Optional[int] = None
    model: Optional[str] = None

    def to_dict(self) -> dict:
        """Converts the ClassificationResult to a dictionary for serialization."""
        data = {
            "segment_index": self.segment_index,
            "classification": self.classification.value,  # Serialize as string
            "classification_type": self.classification_type.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "character": self.character,
        }
        if self.speaker_label:
            data["speaker_label"] = self.speaker_label
        if self.speaker_name:
            data["speaker_name"] = self.speaker_name
        if self.speaker_role:
            data["speaker_role"] = self.speaker_role
        if self.character_confidence is not None:
            data["character_confidence"] = self.character_confidence
        data["unknown_speaker"] = self.unknown_speaker
        if self.temporal_metadata:
            data["temporal_metadata"] = self.temporal_metadata
        if self.prompt_hash:
            data["prompt_hash"] = self.prompt_hash
        if self.response_hash:
            data["response_hash"] = self.response_hash
        if self.prompt_preview:
            data["prompt_preview"] = self.prompt_preview
        if self.response_preview:
            data["response_preview"] = self.response_preview
        if self.generation_latency_ms is not None:
            data["generation_latency_ms"] = self.generation_latency_ms
        if self.model:
            data["model"] = self.model
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ClassificationResult":
        """Creates a ClassificationResult from a dictionary."""
        classification_type = data.get("classification_type", ClassificationType.UNKNOWN.value)
        try:
            classification_type_enum = ClassificationType(classification_type)
        except ValueError:
            classification_type_enum = ClassificationType.UNKNOWN

        return cls(
            segment_index=data["segment_index"],
            classification=Classification(data["classification"]),  # Parse from string
            confidence=data["confidence"],
            reasoning=data["reasoning"],
            character=data.get("character"),
            classification_type=classification_type_enum,
            speaker_label=data.get("speaker_label"),
            speaker_name=data.get("speaker_name"),
            speaker_role=data.get("speaker_role"),
            character_confidence=data.get("character_confidence"),
            unknown_speaker=data.get("unknown_speaker", False),
            temporal_metadata=data.get("temporal_metadata"),
            prompt_hash=data.get("prompt_hash"),
            response_hash=data.get("response_hash"),
            prompt_preview=data.get("prompt_preview"),
            response_preview=data.get("response_preview"),
            generation_latency_ms=data.get("generation_latency_ms"),
            model=data.get("model"),
        )


@dataclass
class SpeakerInfo:
    """Resolved speaker information for prompt building."""
    label: str
    name: Optional[str] = None
    character: Optional[str] = None
    role: str = "UNKNOWN"
    confidence: Optional[float] = None
    unknown: bool = False

    def display_name(self) -> str:
        """Readable representation for prompts/logging."""
        name_parts = [part for part in [self.name, self.character] if part]
        human_label = " / ".join(name_parts)
        if human_label:
            return f"{human_label} ({self.label})"
        return self.label


class BaseClassifier(ABC):
    """Abstract base for IC/OOC classifiers"""

    @abstractmethod
    def classify_segments(
        self,
        segments: List[Dict],
        character_names: List[str],
        player_names: List[str],
        speaker_map: Optional[Dict[str, Dict[str, Any]]] = None,
        temporal_metadata: Optional[List[Dict[str, Any]]] = None
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
        classification_type = ClassificationType.UNKNOWN
        confidence = ConfidenceDefaults.DEFAULT
        reasoning = "Could not parse response"
        character = None
        speaker_name = None

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

        type_match = re.search(r'(?:Type|Categorie):\s*(\w+)', response, re.IGNORECASE)
        if type_match:
            type_text = type_match.group(1).strip().upper()
            try:
                classification_type = ClassificationType(type_text)
            except ValueError:
                self.logger.debug("Unknown classification type '%s' for segment %s", type_text, index)

        # Extract reasoning - capture everything after "Reden:" until next field or end
        reden_match = re.search(
            r'Reden:\s*(.+?)(?=(?:Vertrouwen:|Personage:|Type:|Categorie:|Speaker:|Spreker:|$))',
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

        speaker_match = re.search(r'(?:Spreker|Speaker):\s*(.+?)(?:\n|$)', response, re.IGNORECASE)
        if speaker_match:
            speaker_text = speaker_match.group(1).strip()
            if speaker_text.upper() != "N/A":
                speaker_name = speaker_text

        return ClassificationResult(
            segment_index=index,
            classification=classification,
            confidence=confidence,
            reasoning=reasoning,
            character=character,
            classification_type=classification_type,
            speaker_name=speaker_name,
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

        # Load batch prompt template
        batch_prompt_path = Config.PROJECT_ROOT / "src" / "prompts" / f"classifier_batch_prompt_{Config.WHISPER_LANGUAGE}.txt"
        if not batch_prompt_path.exists():
            self.logger.warning(f"Batch prompt file for language '{Config.WHISPER_LANGUAGE}' not found. Falling back to English.")
            batch_prompt_path = Config.PROJECT_ROOT / "src" / "prompts" / "classifier_batch_prompt_en.txt"

        try:
            with open(batch_prompt_path, 'r', encoding='utf-8') as f:
                self.batch_prompt_template = f.read()
        except FileNotFoundError:
             # Fallback to non-batch if file is missing, but log warning
            self.logger.warning(f"Batch prompt file not found at: {batch_prompt_path}. Batching might fail.")
            self.batch_prompt_template = ""

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

        self.audit_mode = Config.CLASSIFIER_AUDIT_MODE
        self.prompt_preview_length = Config.CLASSIFIER_PROMPT_PREVIEW_CHARS
        self.max_context_segments = Config.CLASSIFIER_CONTEXT_MAX_SEGMENTS
        self.max_past_duration = Config.CLASSIFIER_CONTEXT_PAST_SECONDS
        self.max_future_duration = Config.CLASSIFIER_CONTEXT_FUTURE_SECONDS
        self.use_batching = Config.CLASSIFICATION_USE_BATCHING
        self.batch_size = Config.CLASSIFICATION_BATCH_SIZE

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
        player_names: List[str],
        speaker_map: Optional[Dict[str, Dict[str, Any]]] = None,
        temporal_metadata: Optional[List[Dict[str, Any]]] = None
    ) -> List[ClassificationResult]:
        """Classify each segment using LLM reasoning."""
        if not segments:
            return []

        # If batching is enabled and templates exist, use batched method
        if self.use_batching and self.batch_prompt_template:
            return self.classify_segments_batched(
                segments, character_names, player_names, speaker_map, temporal_metadata
            )

        active_speaker_map = speaker_map or self._build_fallback_speaker_map(segments)
        speaker_overview = self._format_speaker_overview(active_speaker_map)
        session_duration = self._get_session_duration(segments)
        past_classifications: List[Classification] = []
        results: List[ClassificationResult] = []

        # Get session_id from first segment if available for status tracking
        session_id = segments[0].get("session_id", "unknown") if segments else "unknown"

        total_segments = len(segments)
        start_time_all = time.time()

        # Log start
        self.logger.info(f"Starting sequential classification for {total_segments} segments")
        StatusTracker.update_stage(session_id, 6, "running", f"Classifying {total_segments} segments...")

        PROGRESS_INTERVAL = 20  # Log every 20 segments

        for i, segment in enumerate(segments):
            # Progress Logging
            if (i + 1) % PROGRESS_INTERVAL == 0:
                elapsed = time.time() - start_time_all
                avg_time = elapsed / (i + 1)
                remaining = (total_segments - (i + 1)) * avg_time
                percentage = ((i + 1) / total_segments) * 100

                msg = f"Classified {i + 1}/{total_segments} ({percentage:.1f}%) - ETA: {remaining/60:.1f}m"
                self.logger.info(msg)
                StatusTracker.update_stage(session_id, 6, "running", msg)

            context_segments = self._gather_context_segments(segments, i)
            speaker_info = self._resolve_speaker_info(segment.get("speaker"), active_speaker_map)
            metadata = (
                temporal_metadata[i]
                if temporal_metadata and i < len(temporal_metadata)
                else self._build_temporal_metadata(
                    i,
                    segment,
                    segments,
                    past_classifications,
                    session_duration
                )
            )

            prompt_text = self._build_prompt_with_context(
                character_names=character_names,
                player_names=player_names,
                speaker_overview=speaker_overview,
                metadata=metadata,
                context_segments=context_segments,
                speaker_info=speaker_info,
                speaker_map=active_speaker_map,
            )

            result = self._classify_with_context(
                prompt_text,
                index=i,
                speaker_info=speaker_info,
                metadata=metadata,
            )
            results.append(result)
            past_classifications.append(result.classification)

        total_time = time.time() - start_time_all
        avg_time = total_time / total_segments if total_segments > 0 else 0
        self.logger.info(f"Classification complete: {total_segments} segments in {total_time/60:.1f} minutes ({avg_time:.2f}s per segment)")

        return results

    def classify_segments_batched(
        self,
        segments: List[Dict],
        character_names: List[str],
        player_names: List[str],
        speaker_map: Optional[Dict[str, Dict[str, Any]]] = None,
        temporal_metadata: Optional[List[Dict[str, Any]]] = None
    ) -> List[ClassificationResult]:
        """Classify segments in batches for performance optimization."""
        active_speaker_map = speaker_map or self._build_fallback_speaker_map(segments)
        speaker_overview = self._format_speaker_overview(active_speaker_map)

        results: List[ClassificationResult] = [None] * len(segments)
        total_segments = len(segments)
        session_id = segments[0].get("session_id", "unknown") if segments else "unknown"

        self.logger.info(f"Starting batched classification for {total_segments} segments (batch size: {self.batch_size})")
        StatusTracker.update_stage(session_id, 6, "running", f"Batch classifying {total_segments} segments...")

        start_time_all = time.time()

        for i in range(0, total_segments, self.batch_size):
            batch_segments = segments[i : min(i + self.batch_size, total_segments)]
            batch_indices = list(range(i, i + len(batch_segments)))

            # Prepare batch text
            batch_text_lines = []
            for idx, seg in zip(batch_indices, batch_segments):
                info = self._resolve_speaker_info(seg.get("speaker"), active_speaker_map)
                timestamp = self._format_timestamp(seg.get("start_time"))
                batch_text_lines.append(f"Index {idx} [{timestamp}] {info.display_name()}: {seg.get('text', '').strip()}")

            batch_text = "\n".join(batch_text_lines)

            prompt = self.batch_prompt_template.format(
                char_list=", ".join(character_names) if character_names else "Unknown",
                player_list=", ".join(player_names) if player_names else "Unknown",
                speaker_map=speaker_overview,
                batch_text=batch_text
            )

            # Progress logging
            if i > 0:
                elapsed = time.time() - start_time_all
                processed = i
                avg_time_per_segment = elapsed / processed
                remaining = (total_segments - processed) * avg_time_per_segment
                percentage = (processed / total_segments) * 100
                msg = f"Classified {processed}/{total_segments} ({percentage:.1f}%) - ETA: {remaining/60:.1f}m"
                self.logger.info(msg)
                StatusTracker.update_stage(session_id, 6, "running", msg)

            try:
                response_payload = self._generate_with_retry(prompt, i)

                if response_payload:
                    response_text = response_payload.get("response", "")
                    parsed_results = self._parse_batch_response(response_text, batch_indices)

                    # Fill in results
                    for res in parsed_results:
                        idx = res.segment_index
                        if i <= idx < i + self.batch_size:
                            # Enrich result with metadata/context logic as in single mode
                            # Note: context-aware classification is reduced in batched mode,
                            # relying more on the LLM's ability to see local context in the batch
                            speaker_info = self._resolve_speaker_info(segments[idx].get("speaker"), active_speaker_map)

                            res.model = response_payload.get("model")
                            self._apply_speaker_metadata(res, speaker_info)
                            self._infer_classification_type(res, speaker_info)
                            self._attach_prompt_metadata(res, prompt, response_text)

                            results[idx] = res

            except Exception as e:
                self.logger.error(f"Batch classification failed for indices {batch_indices}: {e}")
                # Will be handled by fallback loop

        # Fill in any missing results (failed batches)
        failed_indices = [idx for idx, res in enumerate(results) if res is None]
        if failed_indices:
            self.logger.warning(f"Falling back to sequential classification for {len(failed_indices)} failed segments")

            # Group contiguous indices into mini-batches for efficiency if we want,
            # but for safety let's just process them sequentially using the existing helper methods.
            for idx in failed_indices:
                segment = segments[idx]
                context_segments = self._gather_context_segments(segments, idx)
                speaker_info = self._resolve_speaker_info(segment.get("speaker"), active_speaker_map)

                metadata = (
                    temporal_metadata[idx]
                    if temporal_metadata and idx < len(temporal_metadata)
                    else self._build_temporal_metadata(
                        idx,
                        segment,
                        segments,
                        # Pass recent classifications if available, else empty list
                        [r.classification for r in results[:idx] if r],
                        self._get_session_duration(segments)
                    )
                )

                prompt_text = self._build_prompt_with_context(
                    character_names=character_names,
                    player_names=player_names,
                    speaker_overview=speaker_overview,
                    metadata=metadata,
                    context_segments=context_segments,
                    speaker_info=speaker_info,
                    speaker_map=active_speaker_map,
                )

                # Use sequential classification helper
                results[idx] = self._classify_with_context(
                    prompt_text,
                    index=idx,
                    speaker_info=speaker_info,
                    metadata=metadata,
                )

        total_time = time.time() - start_time_all
        avg_time = total_time / total_segments if total_segments > 0 else 0
        self.logger.info(f"Batch classification complete: {total_segments} segments in {total_time/60:.1f} minutes ({avg_time:.2f}s per segment)")

        return results

    def _parse_batch_response(self, response_text: str, expected_indices: List[int]) -> List[ClassificationResult]:
        """Parse JSON response from batch classification."""
        import json

        # Try to find JSON array in the text
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if not json_match:
            self.logger.warning("No JSON array found in batch response")
            return []

        json_str = json_match.group(0)
        results = []

        try:
            data = json.loads(json_str)
            for item in data:
                index = item.get("index")
                if index not in expected_indices:
                    continue

                # Parse fields
                classification = Classification.IN_CHARACTER
                try:
                    classification = Classification(item.get("classification", "IC").upper())
                except ValueError:
                    pass

                classification_type = ClassificationType.UNKNOWN
                try:
                    classification_type = ClassificationType(item.get("type", "UNKNOWN").upper())
                except ValueError:
                    pass

                confidence = float(item.get("confidence", ConfidenceDefaults.DEFAULT))

                results.append(ClassificationResult(
                    segment_index=index,
                    classification=classification,
                    classification_type=classification_type,
                    confidence=confidence,
                    reasoning=item.get("reason", ""),
                    character=item.get("character"),
                    speaker_name=item.get("speaker_name")
                ))

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON from batch response: {e}")

        return results

    def _classify_with_context(
        self,
        prompt: str,
        index: int,
        speaker_info: SpeakerInfo,
        metadata: Dict[str, Any],
    ) -> ClassificationResult:
        """Classify a single segment with context."""
        start = time.perf_counter()
        response_payload = self._generate_with_retry(prompt, index)
        latency_ms = int((time.perf_counter() - start) * 1000)

        if response_payload is None:
            result = ClassificationResult(
                segment_index=index,
                classification=Classification.IN_CHARACTER,
                confidence=ConfidenceDefaults.DEFAULT,
                reasoning="Classification failed, defaulted to IC",
                classification_type=ClassificationType.UNKNOWN,
            )
            response_text = ""
        else:
            response_text = response_payload.get("response", "")
            result = self._parse_response(response_text, index)
            result.model = response_payload.get("model")

        result.generation_latency_ms = latency_ms
        result.temporal_metadata = metadata
        self._apply_speaker_metadata(result, speaker_info)
        self._infer_classification_type(result, speaker_info)
        self._attach_prompt_metadata(result, prompt, response_text)
        return result

    def _build_prompt_with_context(
        self,
        *,
        character_names: List[str],
        player_names: List[str],
        speaker_overview: str,
        metadata: Dict[str, Any],
        context_segments: Dict[str, Any],
        speaker_info: SpeakerInfo,
        speaker_map: Dict[str, Dict[str, Any]],
    ) -> str:
        char_list = ", ".join(character_names) if character_names else "Unknown"
        player_list = ", ".join(player_names) if player_names else "Unknown"

        metadata_block = self._format_metadata_block(metadata)
        past_context = self._format_context_block(
            context_segments["past"],
            speaker_map,
            reverse=True,
        )
        future_context = self._format_context_block(
            context_segments["future"],
            speaker_map,
            reverse=False,
        )

        prev_text = "\n".join(
            [
                "Sprekerkaart:",
                speaker_overview or "geen bekende sprekerinformatie",
                "",
                "Metadata huidig segment:",
                metadata_block,
                "",
                "Recente context (meest recent eerst):",
                past_context or "[geen eerdere context]",
            ]
        )
        current_text = self._format_segment_line(context_segments["current"], speaker_info)
        next_text = "\n".join(
            [
                "Aankomende context:",
                future_context or "[geen toekomstige context]",
            ]
        )

        return self.prompt_template.format(
            char_list=char_list,
            player_list=player_list,
            prev_text=prev_text,
            current_text=current_text,
            next_text=next_text,
        )

    def _format_metadata_block(self, metadata: Dict[str, Any]) -> str:
        recent = metadata.get("recent_classifications") or []
        recent_text = ", ".join(recent) if recent else "geen"
        return (
            f"Tijdstempel: {metadata.get('timestamp', '00:00:00')} "
            f"({metadata.get('session_offset', 0.0):.2f}s in sessie)\n"
            f"Fase: {metadata.get('phase', 'in-progress')}\n"
            f"Turn-rate (30s): {metadata.get('turn_rate', 0.0):.2f} beurten/seconde\n"
            f"Recente classificaties: {recent_text}"
        )

    def _format_context_block(
        self,
        segments: List[Dict[str, Any]],
        speaker_map: Dict[str, Dict[str, Any]],
        *,
        reverse: bool,
    ) -> str:
        if not segments:
            return ""

        ordered_segments = reversed(segments) if reverse else segments
        lines = []
        for seg in ordered_segments:
            info = self._resolve_speaker_info(seg.get("speaker"), speaker_map)
            lines.append(self._format_segment_line(seg, info))
        return "\n".join(lines)

    def _format_segment_line(self, segment: Dict[str, Any], speaker_info: SpeakerInfo) -> str:
        timestamp = self._format_timestamp(segment.get("start_time"))
        text = (segment.get("text") or "").strip()
        return f"[{timestamp}] {speaker_info.display_name()}: {text}"

    def _format_timestamp(self, value: Optional[float]) -> str:
        value = float(value or 0.0)
        hours = int(value // 3600)
        minutes = int((value % 3600) // 60)
        seconds = int(value % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _get_session_duration(self, segments: List[Dict[str, Any]]) -> float:
        if not segments:
            return 0.0
        tail = segments[-1]
        return float(tail.get("end_time") or tail.get("start_time") or 0.0)

    def _gather_context_segments(self, segments: List[Dict[str, Any]], index: int) -> Dict[str, Any]:
        current = segments[index]
        start_time = float(current.get("start_time") or 0.0)

        past: List[Dict[str, Any]] = []
        future: List[Dict[str, Any]] = []

        for j in range(index - 1, -1, -1):
            if len(past) >= self.max_context_segments:
                break
            candidate = segments[j]
            delta = start_time - float(candidate.get("start_time") or 0.0)
            if delta > self.max_past_duration:
                break
            past.append(candidate)

        for j in range(index + 1, len(segments)):
            if len(future) >= self.max_context_segments:
                break
            candidate = segments[j]
            delta = float(candidate.get("start_time") or 0.0) - start_time
            if delta > self.max_future_duration:
                break
            future.append(candidate)

        return {"current": current, "past": past, "future": future}

    def _build_temporal_metadata(
        self,
        index: int,
        segment: Dict[str, Any],
        segments: List[Dict[str, Any]],
        past_classifications: List[Classification],
        session_duration: float,
    ) -> Dict[str, Any]:
        start = float(segment.get("start_time") or 0.0)
        recent_labels = [c.value for c in past_classifications[-4:]]
        turn_rate = self._calculate_turn_rate(index, segments, window_seconds=30.0)
        phase_ratio = start / session_duration if session_duration else 0.0
        if phase_ratio < 0.15:
            phase = "start"
        elif phase_ratio > 0.85:
            phase = "wrap-up"
        else:
            phase = "in-progress"

        return {
            "timestamp": self._format_timestamp(start),
            "session_offset": start,
            "turn_rate": round(turn_rate, 2),
            "recent_classifications": recent_labels,
            "phase": phase,
        }

    def _calculate_turn_rate(
        self,
        index: int,
        segments: List[Dict[str, Any]],
        window_seconds: float,
    ) -> float:
        if index == 0:
            return 0.0

        current_start = float(segments[index].get("start_time") or 0.0)
        window_start = current_start - window_seconds
        count = 0
        earliest = current_start

        for j in range(index - 1, -1, -1):
            candidate_start = float(segments[j].get("start_time") or 0.0)
            if candidate_start < window_start:
                break
            earliest = candidate_start
            count += 1

        time_span = current_start - earliest
        if time_span <= 0:
            return float(count)
        return count / time_span

    def _build_fallback_speaker_map(self, segments: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        fallback: Dict[str, Dict[str, Any]] = {}
        for segment in segments:
            label = segment.get("speaker") or "UNKNOWN"
            fallback.setdefault(label, {"role": "UNKNOWN"})
        return fallback

    def _format_speaker_overview(self, speaker_map: Dict[str, Dict[str, Any]]) -> str:
        if not speaker_map:
            return "Geen bekende sprekerinformatie beschikbaar."

        lines = []
        for label in sorted(speaker_map.keys()):
            entry = speaker_map[label] or {}
            name = entry.get("name") or entry.get("player_name")
            character = entry.get("character") or entry.get("character_name")
            role = (entry.get("role") or ("PLAYER" if character else "UNKNOWN")).upper()
            details = ", ".join([item for item in [name, character, role] if item])
            lines.append(f"{label}: {details or role}")
        return "\n".join(lines)

    def _resolve_speaker_info(
        self,
        speaker_id: Optional[str],
        speaker_map: Dict[str, Dict[str, Any]],
    ) -> SpeakerInfo:
        label = speaker_id or "UNKNOWN"
        entry = speaker_map.get(label, {})
        name = entry.get("name") or entry.get("player_name")
        character = entry.get("character") or entry.get("character_name")
        role = entry.get("role") or ("PLAYER" if character else "UNKNOWN")
        return SpeakerInfo(
            label=label,
            name=name,
            character=character,
            role=str(role).upper(),
            confidence=entry.get("confidence"),
            unknown=entry.get("unknown_speaker", False),
        )

    def _apply_speaker_metadata(self, result: ClassificationResult, speaker_info: SpeakerInfo) -> None:
        result.speaker_label = speaker_info.label
        if not result.speaker_name and speaker_info.name:
            result.speaker_name = speaker_info.name
        result.speaker_role = speaker_info.role
        result.character_confidence = speaker_info.confidence
        result.unknown_speaker = speaker_info.unknown
        if not result.character and speaker_info.character:
            result.character = speaker_info.character

    def _infer_classification_type(self, result: ClassificationResult, speaker_info: SpeakerInfo) -> None:
        if result.classification_type != ClassificationType.UNKNOWN:
            return

        role = (speaker_info.role or "UNKNOWN").upper()
        if result.classification == Classification.IN_CHARACTER:
            if role == "DM_NARRATOR":
                result.classification_type = ClassificationType.DM_NARRATION
            elif role == "DM_NPC":
                result.classification_type = ClassificationType.NPC_DIALOGUE
            else:
                result.classification_type = ClassificationType.CHARACTER
        elif result.classification == Classification.OUT_OF_CHARACTER:
            result.classification_type = ClassificationType.OOC_OTHER

    def _attach_prompt_metadata(self, result: ClassificationResult, prompt: str, response_text: str) -> None:
        result.prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        result.response_hash = hashlib.sha256(response_text.encode("utf-8")).hexdigest() if response_text else None
        if self.audit_mode:
            result.prompt_preview = prompt[: self.prompt_preview_length]
            result.response_preview = response_text[: self.prompt_preview_length] if response_text else None

    def _generate_with_retry(self, prompt: str, index: int) -> Optional[Dict[str, Any]]:
        try:
            return self._generate_with_model(self.model, prompt)
        except Exception as exc:
            low_vram_response = self._maybe_retry_with_low_vram(prompt, index, exc)
            if low_vram_response is not None:
                return low_vram_response

            fallback_response = self._maybe_retry_with_fallback(prompt, index, exc)
            if fallback_response is not None:
                return fallback_response

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
        player_names: List[str],
        speaker_map: Optional[Dict[str, Dict[str, Any]]] = None,
        temporal_metadata: Optional[List[Dict[str, Any]]] = None
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
        player_names: List[str],
        speaker_map: Optional[Dict[str, Dict[str, Any]]] = None,
        temporal_metadata: Optional[List[Dict[str, Any]]] = None
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
