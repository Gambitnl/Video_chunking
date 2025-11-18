"""
Scene Builder Module

Bundles classification segments into narrative scenes for improved story extraction.
Implements Topic 7 (Scene-Level Segment Bundles) from IC_OOC_CLASSIFICATION_ANALYSIS.md.

Scene detection uses combined heuristics:
- Classification changes (IC <-> OOC flips)
- Time-based gaps (>60-90s silence)
- Speaker roster changes (optional, for advanced use cases)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger("DDSessionProcessor.scene_builder")


@dataclass
class SceneState:
    """
    Tracks the state of a scene being built.

    Accumulates segments and calculates scene metadata (duration, speakers, etc.)
    """
    scene_index: int
    segments: List[Dict[str, Any]] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    speakers: set = field(default_factory=set)
    classification_counts: Dict[str, int] = field(default_factory=dict)
    confidence_min: Optional[float] = None
    confidence_max: Optional[float] = None

    def add(self, segment: Dict[str, Any], classification: Dict[str, Any]) -> None:
        """Add a segment to the current scene."""
        self.segments.append({
            "segment": segment,
            "classification": classification
        })

        # Update scene boundaries
        seg_start = segment.get("start_time", 0.0)
        seg_end = segment.get("end_time", 0.0)

        if self.start_time is None or seg_start < self.start_time:
            self.start_time = seg_start
        if self.end_time is None or seg_end > self.end_time:
            self.end_time = seg_end

        # Track speakers
        speaker = segment.get("speaker")
        if speaker:
            self.speakers.add(speaker)

        # Track classification types
        classif_type = classification.get("classification_type", classification.get("classification", "IC"))
        self.classification_counts[classif_type] = self.classification_counts.get(classif_type, 0) + 1

        # Track confidence range
        confidence = classification.get("confidence", 0.0)
        if self.confidence_min is None or confidence < self.confidence_min:
            self.confidence_min = confidence
        if self.confidence_max is None or confidence > self.confidence_max:
            self.confidence_max = confidence

    def should_break(
        self,
        segment: Dict[str, Any],
        classification: Dict[str, Any],
        max_gap_seconds: float = 75.0,
        check_classification_change: bool = True
    ) -> bool:
        """
        Determine if a new scene should start.

        Args:
            segment: Current segment being considered
            classification: Classification result for current segment
            max_gap_seconds: Maximum silence gap before starting new scene (default 75s)
            check_classification_change: Whether to break on IC/OOC classification changes

        Returns:
            True if a new scene should start, False to continue current scene
        """
        if not self.segments:
            return False  # Empty scene, can't break yet

        last_seg = self.segments[-1]["segment"]
        last_classif = self.segments[-1]["classification"]

        # Check for time gap
        time_gap = segment.get("start_time", 0.0) - last_seg.get("end_time", 0.0)
        if time_gap > max_gap_seconds:
            logger.debug(f"Scene break: time gap {time_gap:.1f}s > {max_gap_seconds}s")
            return True

        # Check for classification change (IC <-> OOC flip)
        if check_classification_change:
            last_classif_primary = last_classif.get("classification", "IC")
            current_classif_primary = classification.get("classification", "IC")

            # Break on IC <-> OOC flip (but not IC <-> MIXED or OOC <-> MIXED)
            if (last_classif_primary == "IC" and current_classif_primary == "OOC") or \
               (last_classif_primary == "OOC" and current_classif_primary == "IC"):
                logger.debug(f"Scene break: classification change {last_classif_primary} -> {current_classif_primary}")
                return True

        return False

    def finalize(self, summary_mode: str = "template") -> Dict[str, Any]:
        """
        Finalize the scene and return scene metadata.

        Args:
            summary_mode: How to generate summary ("template", "llm", "none")

        Returns:
            Scene dictionary with all metadata
        """
        if not self.segments:
            return {}

        # Determine dominant classification type
        dominant_type = max(self.classification_counts.items(), key=lambda x: x[1])[0] if self.classification_counts else "IC"

        scene_data = {
            "scene_index": self.scene_index,
            "start_time": self.start_time or 0.0,
            "end_time": self.end_time or 0.0,
            "duration": (self.end_time or 0.0) - (self.start_time or 0.0),
            "dominant_type": dominant_type,
            "speaker_list": sorted(list(self.speakers)),
            "segment_count": len(self.segments),
            "classification_distribution": dict(self.classification_counts),
        }

        # Add confidence span
        if self.confidence_min is not None and self.confidence_max is not None:
            scene_data["confidence_span"] = {
                "min": round(self.confidence_min, 2),
                "max": round(self.confidence_max, 2),
            }

        # Generate summary based on mode
        if summary_mode == "template":
            scene_data["summary"] = self._generate_template_summary()
        elif summary_mode == "llm":
            scene_data["summary"] = "[LLM summary not yet implemented - placeholder]"
        # If mode is "none", no summary is added

        return scene_data

    def _generate_template_summary(self) -> str:
        """Generate a simple template-based summary."""
        if not self.segments:
            return "Empty scene"

        speaker_names = ", ".join(self.speakers) if self.speakers else "unknown speakers"
        dominant_type = max(self.classification_counts.items(), key=lambda x: x[1])[0] if self.classification_counts else "IC"
        segment_count = len(self.segments)

        duration_min = int((self.end_time or 0.0) - (self.start_time or 0.0)) // 60
        duration_sec = int((self.end_time or 0.0) - (self.start_time or 0.0)) % 60

        if dominant_type in ["CHARACTER", "DM_NARRATION", "NPC_DIALOGUE"]:
            activity = "in-character roleplay"
        else:
            activity = "out-of-character discussion"

        return f"{speaker_names} - {segment_count} segments of {activity} ({duration_min}m {duration_sec}s)"


class SceneBuilder:
    """
    Builds narrative scenes from classified segments.

    Usage:
        builder = SceneBuilder(max_gap_seconds=75.0)
        scenes = builder.build_scenes(segments, classifications, summary_mode="template")
    """

    def __init__(
        self,
        max_gap_seconds: float = 75.0,
        check_classification_change: bool = True
    ):
        """
        Initialize the scene builder.

        Args:
            max_gap_seconds: Maximum silence gap before starting new scene
            check_classification_change: Whether to break on IC/OOC changes
        """
        self.max_gap_seconds = max_gap_seconds
        self.check_classification_change = check_classification_change

    def build_scenes(
        self,
        segments: List[Dict[str, Any]],
        classifications: List[Dict[str, Any]],
        summary_mode: str = "template"
    ) -> List[Dict[str, Any]]:
        """
        Build scene bundles from segments and classifications.

        Args:
            segments: List of speaker-labeled segment dictionaries
            classifications: List of classification result dictionaries
            summary_mode: How to generate summaries ("template", "llm", "none")

        Returns:
            List of scene dictionaries
        """
        if len(segments) != len(classifications):
            logger.warning(f"Segment/classification count mismatch: {len(segments)} vs {len(classifications)}")
            return []

        scenes = []
        current_scene = SceneState(scene_index=0)

        for seg, classif in zip(segments, classifications):
            # Check if we should start a new scene
            if current_scene.should_break(
                seg,
                classif,
                max_gap_seconds=self.max_gap_seconds,
                check_classification_change=self.check_classification_change
            ):
                # Finalize current scene
                scene_data = current_scene.finalize(summary_mode=summary_mode)
                if scene_data:
                    scenes.append(scene_data)

                # Start new scene
                current_scene = SceneState(scene_index=len(scenes))

            # Add segment to current scene
            current_scene.add(seg, classif)

        # Finalize last scene
        scene_data = current_scene.finalize(summary_mode=summary_mode)
        if scene_data:
            scenes.append(scene_data)

        logger.info(f"Built {len(scenes)} scenes from {len(segments)} segments")
        return scenes

    def calculate_statistics(self, scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate summary statistics across all scenes.

        Args:
            scenes: List of scene dictionaries

        Returns:
            Dictionary with scene statistics
        """
        if not scenes:
            return {}

        total_duration = sum(s.get("duration", 0.0) for s in scenes)
        total_segments = sum(s.get("segment_count", 0) for s in scenes)

        # Calculate average scene duration
        avg_duration = total_duration / len(scenes) if scenes else 0.0

        # Calculate dominant types distribution
        type_counts: Dict[str, int] = {}
        for scene in scenes:
            dominant_type = scene.get("dominant_type", "IC")
            type_counts[dominant_type] = type_counts.get(dominant_type, 0) + 1

        # Find most common speakers across all scenes
        all_speakers: Dict[str, int] = {}
        for scene in scenes:
            for speaker in scene.get("speaker_list", []):
                all_speakers[speaker] = all_speakers.get(speaker, 0) + 1

        top_speakers = sorted(all_speakers.items(), key=lambda x: -x[1])[:5]

        return {
            "total_scenes": len(scenes),
            "total_duration": round(total_duration, 2),
            "total_segments": total_segments,
            "avg_scene_duration": round(avg_duration, 2),
            "scene_type_distribution": type_counts,
            "top_speakers": [{"speaker": s, "scene_count": c} for s, c in top_speakers],
        }
