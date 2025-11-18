"""Tests for constants module"""
import pytest
from src.constants import (
    Classification,
    ProcessingStatus,
    PipelineStage,
    OutputFormat,
    SpeakerLabel,
    ConfidenceDefaults,
    TimeConstants,
)


class TestClassification:
    def test_enum_values(self):
        assert Classification.IN_CHARACTER.value == "IC"
        assert Classification.OUT_OF_CHARACTER.value == "OOC"
        assert Classification.MIXED.value == "MIXED"

    def test_string_conversion(self):
        assert str(Classification.IN_CHARACTER) == "IC"
        assert str(Classification.OUT_OF_CHARACTER) == "OOC"
        assert str(Classification.MIXED) == "MIXED"

    def test_string_comparison(self):
        """Ensure enums work in string comparisons"""
        assert Classification.IN_CHARACTER == "IC"
        assert Classification.OUT_OF_CHARACTER == "OOC"
        assert Classification.MIXED == "MIXED"

    def test_display_name(self):
        assert "In-Character" in Classification.IN_CHARACTER.display_name
        assert "Out-of-Character" in Classification.OUT_OF_CHARACTER.display_name
        assert "Mixed" in Classification.MIXED.display_name

    def test_from_string(self):
        """Test that we can create Classification from string"""
        assert Classification("IC") == Classification.IN_CHARACTER
        assert Classification("OOC") == Classification.OUT_OF_CHARACTER
        assert Classification("MIXED") == Classification.MIXED

    def test_invalid_string(self):
        """Test that invalid string raises ValueError"""
        with pytest.raises(ValueError):
            Classification("INVALID")


class TestProcessingStatus:
    def test_enum_values(self):
        assert ProcessingStatus.RUNNING.value == "running"
        assert ProcessingStatus.COMPLETED.value == "completed"
        assert ProcessingStatus.FAILED.value == "failed"
        assert ProcessingStatus.SKIPPED.value == "skipped"
        assert ProcessingStatus.PENDING.value == "pending"

    def test_string_conversion(self):
        assert str(ProcessingStatus.RUNNING) == "running"
        assert str(ProcessingStatus.COMPLETED) == "completed"

    def test_string_comparison(self):
        """Ensure enums work in string comparisons"""
        assert ProcessingStatus.RUNNING == "running"
        assert ProcessingStatus.COMPLETED == "completed"

    def test_is_terminal(self):
        assert ProcessingStatus.COMPLETED.is_terminal()
        assert ProcessingStatus.FAILED.is_terminal()
        assert ProcessingStatus.SKIPPED.is_terminal()
        assert not ProcessingStatus.RUNNING.is_terminal()
        assert not ProcessingStatus.PENDING.is_terminal()

    def test_from_string(self):
        """Test that we can create ProcessingStatus from string"""
        assert ProcessingStatus("running") == ProcessingStatus.RUNNING
        assert ProcessingStatus("completed") == ProcessingStatus.COMPLETED


class TestPipelineStage:
    def test_enum_values(self):
        assert PipelineStage.AUDIO_CONVERTED.value == "audio_converted"
        assert PipelineStage.AUDIO_CHUNKED.value == "audio_chunked"
        assert PipelineStage.AUDIO_TRANSCRIBED.value == "audio_transcribed"
        assert PipelineStage.TRANSCRIPTION_MERGED.value == "transcription_merged"
        assert PipelineStage.SPEAKER_DIARIZED.value == "speaker_diarized"
        assert PipelineStage.SEGMENTS_CLASSIFIED.value == "segments_classified"
        assert PipelineStage.OUTPUTS_GENERATED.value == "outputs_generated"
        assert PipelineStage.AUDIO_SEGMENTS_EXPORTED.value == "audio_segments_exported"
        assert PipelineStage.KNOWLEDGE_EXTRACTED.value == "knowledge_extracted"

    def test_string_conversion(self):
        assert str(PipelineStage.AUDIO_CONVERTED) == "audio_converted"
        assert str(PipelineStage.KNOWLEDGE_EXTRACTED) == "knowledge_extracted"

    def test_string_comparison(self):
        """Ensure enums work in string comparisons"""
        assert PipelineStage.AUDIO_CONVERTED == "audio_converted"
        assert PipelineStage.KNOWLEDGE_EXTRACTED == "knowledge_extracted"

    def test_stage_numbers(self):
        assert PipelineStage.AUDIO_CONVERTED.number == 1
        assert PipelineStage.AUDIO_CHUNKED.number == 2
        assert PipelineStage.AUDIO_TRANSCRIBED.number == 3
        assert PipelineStage.TRANSCRIPTION_MERGED.number == 4
        assert PipelineStage.SPEAKER_DIARIZED.number == 5
        assert PipelineStage.SEGMENTS_CLASSIFIED.number == 6
        assert PipelineStage.OUTPUTS_GENERATED.number == 7
        assert PipelineStage.AUDIO_SEGMENTS_EXPORTED.number == 8
        assert PipelineStage.KNOWLEDGE_EXTRACTED.number == 9

    def test_display_names(self):
        assert "Audio Conversion" in PipelineStage.AUDIO_CONVERTED.display_name
        assert "Transcription" in PipelineStage.AUDIO_TRANSCRIBED.display_name
        assert "Knowledge Extraction" in PipelineStage.KNOWLEDGE_EXTRACTED.display_name

    def test_all_stages_have_numbers(self):
        """Ensure all 9 stages have unique numbers"""
        numbers = [stage.number for stage in PipelineStage]
        assert numbers == list(range(1, 10))

    def test_all_stages_have_display_names(self):
        """Ensure all stages have display names"""
        for stage in PipelineStage:
            assert stage.display_name
            assert len(stage.display_name) > 0

    def test_from_string(self):
        """Test that we can create PipelineStage from string"""
        assert PipelineStage("audio_converted") == PipelineStage.AUDIO_CONVERTED
        assert PipelineStage("knowledge_extracted") == PipelineStage.KNOWLEDGE_EXTRACTED


class TestOutputFormat:
    def test_enum_values(self):
        assert OutputFormat.FULL.value == "full"
        assert OutputFormat.IC_ONLY.value == "ic_only"
        assert OutputFormat.OOC_ONLY.value == "ooc_only"
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.SRT_FULL.value == "srt_full"
        assert OutputFormat.SRT_IC.value == "srt_ic"
        assert OutputFormat.SRT_OOC.value == "srt_ooc"

    def test_string_conversion(self):
        assert str(OutputFormat.FULL) == "full"
        assert str(OutputFormat.JSON) == "json"

    def test_string_comparison(self):
        """Ensure enums work in string comparisons"""
        assert OutputFormat.FULL == "full"
        assert OutputFormat.JSON == "json"

    def test_file_extensions(self):
        assert OutputFormat.JSON.get_file_extension() == "json"
        assert OutputFormat.FULL.get_file_extension() == "txt"
        assert OutputFormat.IC_ONLY.get_file_extension() == "txt"
        assert OutputFormat.OOC_ONLY.get_file_extension() == "txt"
        assert OutputFormat.SRT_FULL.get_file_extension() == "srt"
        assert OutputFormat.SRT_IC.get_file_extension() == "srt"
        assert OutputFormat.SRT_OOC.get_file_extension() == "srt"

    def test_from_string(self):
        """Test that we can create OutputFormat from string"""
        assert OutputFormat("full") == OutputFormat.FULL
        assert OutputFormat("json") == OutputFormat.JSON


class TestSpeakerLabel:
    def test_constants(self):
        assert SpeakerLabel.UNKNOWN == "UNKNOWN"
        assert SpeakerLabel.DEFAULT_PREFIX == "SPEAKER_"

    def test_is_generic_label(self):
        assert SpeakerLabel.is_generic_label("UNKNOWN")
        assert SpeakerLabel.is_generic_label("SPEAKER_00")
        assert SpeakerLabel.is_generic_label("SPEAKER_12")
        assert SpeakerLabel.is_generic_label("SPEAKER_99")
        assert not SpeakerLabel.is_generic_label("Alice")
        assert not SpeakerLabel.is_generic_label("Bob")
        assert not SpeakerLabel.is_generic_label("Player1")
        assert not SpeakerLabel.is_generic_label("")

    def test_format_speaker_number(self):
        assert SpeakerLabel.format_speaker_number(0) == "SPEAKER_00"
        assert SpeakerLabel.format_speaker_number(1) == "SPEAKER_01"
        assert SpeakerLabel.format_speaker_number(5) == "SPEAKER_05"
        assert SpeakerLabel.format_speaker_number(12) == "SPEAKER_12"
        assert SpeakerLabel.format_speaker_number(99) == "SPEAKER_99"

    def test_format_speaker_number_large(self):
        """Test with numbers > 99"""
        assert SpeakerLabel.format_speaker_number(100) == "SPEAKER_100"
        assert SpeakerLabel.format_speaker_number(999) == "SPEAKER_999"


class TestConfidenceDefaults:
    def test_constants(self):
        assert ConfidenceDefaults.DEFAULT == 0.5
        assert ConfidenceDefaults.HIGH == 0.9
        assert ConfidenceDefaults.LOW == 0.3
        assert ConfidenceDefaults.MINIMUM == 0.0
        assert ConfidenceDefaults.MAXIMUM == 1.0

    def test_clamp(self):
        # Test clamping below minimum
        assert ConfidenceDefaults.clamp(-0.5) == 0.0
        assert ConfidenceDefaults.clamp(-1.0) == 0.0
        assert ConfidenceDefaults.clamp(-100.0) == 0.0

        # Test clamping above maximum
        assert ConfidenceDefaults.clamp(1.5) == 1.0
        assert ConfidenceDefaults.clamp(2.0) == 1.0
        assert ConfidenceDefaults.clamp(100.0) == 1.0

        # Test valid range
        assert ConfidenceDefaults.clamp(0.0) == 0.0
        assert ConfidenceDefaults.clamp(0.5) == 0.5
        assert ConfidenceDefaults.clamp(0.7) == 0.7
        assert ConfidenceDefaults.clamp(1.0) == 1.0

        # Test edge cases
        assert ConfidenceDefaults.clamp(0.999999) == 0.999999
        assert ConfidenceDefaults.clamp(0.000001) == 0.000001


class TestTimeConstants:
    def test_constants(self):
        assert TimeConstants.SECONDS_PER_MINUTE == 60
        assert TimeConstants.SECONDS_PER_HOUR == 3600
        assert TimeConstants.MILLISECONDS_PER_SECOND == 1000

    def test_seconds_to_hms(self):
        # Test zero
        assert TimeConstants.seconds_to_hms(0) == (0, 0, 0)

        # Test seconds only
        assert TimeConstants.seconds_to_hms(1) == (0, 0, 1)
        assert TimeConstants.seconds_to_hms(30) == (0, 0, 30)
        assert TimeConstants.seconds_to_hms(59) == (0, 0, 59)

        # Test minutes
        assert TimeConstants.seconds_to_hms(60) == (0, 1, 0)
        assert TimeConstants.seconds_to_hms(90) == (0, 1, 30)
        assert TimeConstants.seconds_to_hms(3599) == (0, 59, 59)

        # Test hours
        assert TimeConstants.seconds_to_hms(3600) == (1, 0, 0)
        assert TimeConstants.seconds_to_hms(3661) == (1, 1, 1)
        assert TimeConstants.seconds_to_hms(7200) == (2, 0, 0)
        assert TimeConstants.seconds_to_hms(7322) == (2, 2, 2)

        # Test complex times
        assert TimeConstants.seconds_to_hms(5400) == (1, 30, 0)
        assert TimeConstants.seconds_to_hms(5430) == (1, 30, 30)
        assert TimeConstants.seconds_to_hms(86400) == (24, 0, 0)  # 1 day

    def test_seconds_to_hms_float(self):
        """Test with float input (should truncate to int)"""
        assert TimeConstants.seconds_to_hms(90.7) == (0, 1, 30)
        assert TimeConstants.seconds_to_hms(3661.9) == (1, 1, 1)


class TestEnumInteroperability:
    """Test that enums work well in common scenarios"""

    def test_enums_in_sets(self):
        """Test that enums can be used in sets"""
        stages = {PipelineStage.AUDIO_CONVERTED, PipelineStage.AUDIO_CHUNKED}
        assert PipelineStage.AUDIO_CONVERTED in stages
        assert PipelineStage.AUDIO_TRANSCRIBED not in stages

    def test_enums_in_dicts(self):
        """Test that enums can be used as dict keys"""
        status_map = {
            ProcessingStatus.RUNNING: "In progress",
            ProcessingStatus.COMPLETED: "Done"
        }
        assert status_map[ProcessingStatus.RUNNING] == "In progress"

    def test_enums_in_lists(self):
        """Test that enums can be used in lists"""
        classifications = [Classification.IN_CHARACTER, Classification.OUT_OF_CHARACTER]
        assert Classification.IN_CHARACTER in classifications
        assert Classification.MIXED not in classifications

    def test_enum_iteration(self):
        """Test that we can iterate over enum members"""
        all_classifications = list(Classification)
        assert len(all_classifications) == 3
        assert Classification.IN_CHARACTER in all_classifications

    def test_enum_json_serialization(self):
        """Test that enum values can be easily serialized"""
        import json

        data = {
            "classification": Classification.IN_CHARACTER.value,
            "status": ProcessingStatus.RUNNING.value,
            "stage": PipelineStage.AUDIO_CONVERTED.value
        }
        json_str = json.dumps(data)
        loaded = json.loads(json_str)

        assert Classification(loaded["classification"]) == Classification.IN_CHARACTER
        assert ProcessingStatus(loaded["status"]) == ProcessingStatus.RUNNING
        assert PipelineStage(loaded["stage"]) == PipelineStage.AUDIO_CONVERTED
