from datetime import datetime
import uuid
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import pytest

from src.pipeline import (
    DDSessionProcessor,
    StageResult,
    PipelineStage,
    ProcessingStatus,
)
from src.classifier import ClassificationResult
from src.constants import Classification, ClassificationType


class DummySegment:
    def __init__(self):
        self.text = "Hi"
        self.start_time = 0.0
        self.end_time = 1.0
        self.speaker = "SPEAKER_00"
        self.confidence = 0.9

    def to_dict(self):
        return {
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "speaker": self.speaker,
        }


def _stage(stage: PipelineStage, data=None) -> StageResult:
    return StageResult(
        stage=stage,
        status=ProcessingStatus.COMPLETED,
        data=data or {},
        start_time=datetime.now(),
        end_time=datetime.now(),
    )


@patch("src.pipeline.HybridChunker")
@patch("src.pipeline.TranscriberFactory")
@patch("src.pipeline.DiarizerFactory")
@patch("src.pipeline.ClassifierFactory")
def test_stage_segments_classification_calls_classifier(
    MockClassifierFactory,
    MockDiarizerFactory,
    MockTranscriberFactory,
    MockHybridChunker,
):
    mock_classifier = MagicMock()
    MockClassifierFactory.create.return_value = mock_classifier
    mock_classifier.classify_segments.return_value = [
        ClassificationResult(
            segment_index=0,
            classification=Classification.IN_CHARACTER,
            classification_type=ClassificationType.CHARACTER,
            confidence=0.94,
            reasoning="Greeting",
        )
    ]

    processor = DDSessionProcessor("stage6_unit")
    processor.character_names = ["Hero"]
    processor.player_names = ["Alice"]

    segments = [
        {"text": "Hello", "start_time": 0.0, "end_time": 1.0, "speaker": "SPEAKER_00"}
    ]

    stage_result = processor._stage_segments_classification(segments, skip_classification=False)

    assert stage_result.status == ProcessingStatus.COMPLETED
    mock_classifier.classify_segments.assert_called_once_with(
        segments,
        ["Hero"],
        ["Alice"],
        progress_callback=ANY,
    )


@patch("src.pipeline.ClassifierFactory")
@patch("src.pipeline.HybridChunker")
@patch("src.pipeline.StatusTracker.update_stage")
def test_stage_segments_classification_reports_progress(
    mock_update_stage,
    MockHybridChunker,
    MockClassifierFactory,
):
    MockClassifierFactory.create.return_value = MagicMock()
    processor = DDSessionProcessor("progress-status")
    processor.character_names = ["Hero"]
    processor.player_names = ["Alice"]

    def _classify_with_progress(segments, character_names, player_names, progress_callback=None):
        if progress_callback:
            progress_callback(1, len(segments))
        return [
            ClassificationResult(
                segment_index=0,
                classification=Classification.IN_CHARACTER,
                classification_type=ClassificationType.CHARACTER,
                confidence=0.9,
                reasoning="Test",
            )
        ]

    processor.classifier = MagicMock()
    processor.classifier.classify_segments.side_effect = _classify_with_progress

    segments = [
        {"text": "Hello", "start_time": 0.0, "end_time": 1.0, "speaker": "SPEAKER_00"}
    ]

    stage_result = processor._stage_segments_classification(segments, skip_classification=False)

    assert stage_result.status == ProcessingStatus.COMPLETED
    progress_messages = [call.args[3] for call in mock_update_stage.call_args_list if len(call.args) >= 4]
    assert any("Classified 1/1 segments" in message for message in progress_messages)


@patch.object(DDSessionProcessor, "_stage_knowledge_extraction")
@patch.object(DDSessionProcessor, "_stage_audio_segments_export")
@patch.object(DDSessionProcessor, "_stage_outputs_generation")
@patch.object(DDSessionProcessor, "_stage_segments_classification")
@patch.object(DDSessionProcessor, "_stage_speaker_diarization")
@patch.object(DDSessionProcessor, "_stage_transcription_merging")
@patch.object(DDSessionProcessor, "_stage_audio_transcription")
@patch.object(DDSessionProcessor, "_stage_audio_chunking")
@patch.object(DDSessionProcessor, "_stage_audio_conversion")
@patch("src.pipeline.HybridChunker")
def test_process_runs_classification_stage(
    MockHybridChunker,
    mock_stage_audio_conversion,
    mock_stage_audio_chunking,
    mock_stage_audio_transcription,
    mock_stage_transcription_merging,
    mock_stage_diarization,
    mock_stage_classification,
    mock_stage_outputs,
    mock_stage_audio_export,
    mock_stage_knowledge,
    tmp_path,
):
    converted_path = tmp_path / "converted.wav"
    converted_path.write_bytes(b"wav")

    mock_stage_audio_conversion.return_value = _stage(
        PipelineStage.AUDIO_CONVERTED,
        {"wav_path": str(converted_path), "duration": 1.0},
    )
    mock_stage_audio_chunking.return_value = _stage(
        PipelineStage.AUDIO_CHUNKED,
        {"chunks": []},
    )
    mock_stage_audio_transcription.return_value = _stage(
        PipelineStage.AUDIO_TRANSCRIBED,
        {"chunk_transcriptions": []},
    )
    merged_segment = DummySegment()
    mock_stage_transcription_merging.return_value = _stage(
        PipelineStage.TRANSCRIPTION_MERGED,
        {"merged_segments": [merged_segment]},
    )
    speaker_segments = [
        {"text": "Hi", "start_time": 0.0, "end_time": 1.0, "speaker": "SPEAKER_00"}
    ]
    mock_stage_diarization.return_value = _stage(
        PipelineStage.SPEAKER_DIARIZED,
        {"speaker_segments_with_labels": speaker_segments},
    )
    classifications = [
        ClassificationResult(
            segment_index=0,
            classification=Classification.IN_CHARACTER,
            classification_type=ClassificationType.CHARACTER,
            confidence=0.95,
            reasoning="Hero speaks",
        )
    ]
    mock_stage_classification.return_value = _stage(
        PipelineStage.SEGMENTS_CLASSIFIED,
        {"classifications": classifications, "ic_count": 1, "ooc_count": 0},
    )
    mock_stage_outputs.return_value = _stage(
        PipelineStage.OUTPUTS_GENERATED,
        {
            "output_files": {"json": str(tmp_path / "out.json")},
            "statistics": {
                "ic_count": 1,
                "ooc_count": 0,
                "total_segments": 1,
                "ic_segments": 1,
                "ooc_segments": 0,
                "ic_percentage": 100.0,
                "total_duration_formatted": "00:00:01",
                "ic_duration_formatted": "00:00:01",
                "character_appearances": {},
            },
            "speaker_profiles": {"SPEAKER_00": "Alice"},
        },
    )
    mock_stage_audio_export.return_value = _stage(
        PipelineStage.AUDIO_SEGMENTS_EXPORTED,
        {"segment_export": {}}
    )
    mock_stage_knowledge.return_value = _stage(
        PipelineStage.KNOWLEDGE_EXTRACTED,
        {"knowledge_data": {}}
    )

    audio_file = tmp_path / "input.wav"
    audio_file.write_bytes(b"audio")

    with patch("src.pipeline.ClassifierFactory") as MockClassifierFactory, \
            patch("src.pipeline.TranscriberFactory") as MockTranscriberFactory, \
            patch("src.pipeline.DiarizerFactory") as MockDiarizerFactory:
        MockClassifierFactory.create.return_value = MagicMock()
        MockTranscriberFactory.create.return_value = MagicMock()
        MockDiarizerFactory.create.return_value = MagicMock()

        session_id = f"pipeline_classification_{uuid.uuid4().hex[:8]}"
        processor = DDSessionProcessor(session_id)
        result = processor.process(
            input_file=audio_file,
            skip_diarization=False,
            skip_classification=False,
            skip_snippets=True,
        )

    assert mock_stage_classification.called
    assert result["statistics"]["ic_count"] == 1
