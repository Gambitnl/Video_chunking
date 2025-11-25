"""Tests for process session UI helpers."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.ui.process_session_helpers import (
    validate_session_id_realtime,
    validate_session_inputs,
    format_statistics_markdown,
    format_snippet_export_markdown,
    format_party_display,
    render_processing_response,
    prepare_processing_status,
    poll_overall_progress,
    poll_transcription_progress,
    poll_runtime_updates,
    check_file_processing_history,
    update_party_display,
)


class TestValidateSessionInputs:
    """Test validation function."""

    def test_valid_inputs_manual_entry(self):
        """Test validation with valid manual entry inputs."""
        audio_file = Mock()
        audio_file.name = "/path/to/test.wav"

        with patch('pathlib.Path.exists', return_value=True):
            errors = validate_session_inputs(
                audio_file=audio_file,
                session_id="session_001",
                party_selection="Manual Entry",
                character_names="Gandalf, Frodo",
                player_names="Alice, Bob",
                num_speakers=4,
            )

        assert errors == []

    def test_valid_inputs_with_party(self):
        """Test validation with valid party selection."""
        audio_file = Mock()
        audio_file.name = "/path/to/test.wav"

        mock_party = Mock()
        mock_party.characters = [Mock(name="Gandalf"), Mock(name="Frodo")]

        with patch('pathlib.Path.exists', return_value=True), \
             patch('src.ui.process_session_helpers.PartyConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.get_party.return_value = mock_party
            mock_manager_class.return_value = mock_manager

            errors = validate_session_inputs(
                audio_file=audio_file,
                session_id="session_001",
                party_selection="test_party",
                character_names="",
                player_names="",
                num_speakers=4,
            )

        assert errors == []

    def test_missing_audio_file(self):
        """Test validation fails when no audio file."""
        errors = validate_session_inputs(
            audio_file=None,
            session_id="session_001",
            party_selection="Manual Entry",
            character_names="Gandalf",
            player_names="Alice",
            num_speakers=4,
        )

        assert len(errors) > 0
        assert any("audio file" in err.lower() for err in errors)

    def test_invalid_audio_extension(self):
        """Test validation fails with unsupported audio format."""
        audio_file = Mock()
        audio_file.name = "/path/to/test.mp4"

        with patch('pathlib.Path.exists', return_value=True):
            errors = validate_session_inputs(
                audio_file=audio_file,
                session_id="session_001",
                party_selection="Manual Entry",
                character_names="Gandalf",
                player_names="",
                num_speakers=4,
            )

        assert any(".mp4" in err for err in errors)

    def test_missing_session_id(self):
        """Test validation fails with missing session ID."""
        audio_file = Mock()
        audio_file.name = "/path/to/test.wav"

        with patch('pathlib.Path.exists', return_value=True):
            errors = validate_session_inputs(
                audio_file=audio_file,
                session_id="",
                party_selection="Manual Entry",
                character_names="Gandalf",
                player_names="",
                num_speakers=4,
            )

        assert any("session id" in err.lower() for err in errors)

    def test_invalid_session_id_characters(self):
        """Test validation fails with invalid session ID characters."""
        audio_file = Mock()
        audio_file.name = "/path/to/test.wav"

        with patch('pathlib.Path.exists', return_value=True):
            errors = validate_session_inputs(
                audio_file=audio_file,
                session_id="invalid session!",  # Spaces and special chars
                party_selection="Manual Entry",
                character_names="Gandalf",
                player_names="",
                num_speakers=4,
            )

        assert any("session id" in err.lower() for err in errors)

    def test_invalid_speaker_count_too_low(self):
        """Test validation fails with speaker count below minimum."""
        audio_file = Mock()
        audio_file.name = "/path/to/test.wav"

        with patch('pathlib.Path.exists', return_value=True):
            errors = validate_session_inputs(
                audio_file=audio_file,
                session_id="session_001",
                party_selection="Manual Entry",
                character_names="Gandalf",
                player_names="",
                num_speakers=1,  # Too low
            )

        assert any("2 and 10" in err for err in errors)

    def test_invalid_speaker_count_too_high(self):
        """Test validation fails with speaker count above maximum."""
        audio_file = Mock()
        audio_file.name = "/path/to/test.wav"

        with patch('pathlib.Path.exists', return_value=True):
            errors = validate_session_inputs(
                audio_file=audio_file,
                session_id="session_001",
                party_selection="Manual Entry",
                character_names="Gandalf",
                player_names="",
                num_speakers=15,  # Too high
            )

        assert any("2 and 10" in err for err in errors)

    def test_duplicate_character_names(self):
        """Test validation catches duplicate character names (case insensitive)."""
        audio_file = Mock()
        audio_file.name = "/path/to/test.wav"

        with patch('pathlib.Path.exists', return_value=True):
            errors = validate_session_inputs(
                audio_file=audio_file,
                session_id="session_001",
                party_selection="Manual Entry",
                character_names="Gandalf, gandalf",  # Duplicate (case insensitive)
                player_names="",
                num_speakers=4,
            )

        assert any("unique" in err.lower() for err in errors)

    def test_mismatched_player_character_counts(self):
        """Test validation fails when player count doesn't match character count."""
        audio_file = Mock()
        audio_file.name = "/path/to/test.wav"

        with patch('pathlib.Path.exists', return_value=True):
            errors = validate_session_inputs(
                audio_file=audio_file,
                session_id="session_001",
                party_selection="Manual Entry",
                character_names="Gandalf, Frodo",
                player_names="Alice",  # Only one player for two characters
                num_speakers=4,
            )

        assert any("player names must match" in err.lower() for err in errors)

    def test_party_not_found(self):
        """Test validation fails when selected party doesn't exist."""
        audio_file = Mock()
        audio_file.name = "/path/to/test.wav"

        with patch('pathlib.Path.exists', return_value=True), \
             patch('src.ui.process_session_helpers.PartyConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.get_party.return_value = None
            mock_manager_class.return_value = mock_manager

            errors = validate_session_inputs(
                audio_file=audio_file,
                session_id="session_001",
                party_selection="nonexistent_party",
                character_names="",
                player_names="",
                num_speakers=4,
            )

        assert any("could not be loaded" in err.lower() for err in errors)

    def test_party_with_no_characters(self):
        """Test validation fails when party has no characters."""
        audio_file = Mock()
        audio_file.name = "/path/to/test.wav"

        mock_party = Mock()
        mock_party.characters = []

        with patch('pathlib.Path.exists', return_value=True), \
             patch('src.ui.process_session_helpers.PartyConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.get_party.return_value = mock_party
            mock_manager_class.return_value = mock_manager

            errors = validate_session_inputs(
                audio_file=audio_file,
                session_id="session_001",
                party_selection="empty_party",
                character_names="",
                player_names="",
                num_speakers=4,
            )

        assert any("no characters" in err.lower() for err in errors)


class TestFormatStatisticsMarkdown:
    """Test statistics formatting."""

    def test_format_with_complete_stats(self):
        """Test formatting valid statistics."""
        stats = {
            "total_duration_formatted": "1:23:45",
            "total_segments": 150,
            "ic_segments": 100,
            "ooc_segments": 50,
        }
        knowledge = {}

        result = format_statistics_markdown(stats, knowledge)

        assert "1:23:45" in result
        assert "150" in result
        assert "100" in result
        assert "50" in result
        assert "Session Statistics" in result

    def test_format_with_knowledge_extraction(self):
        """Test formatting with knowledge extraction data."""
        stats = {"total_segments": 10}
        knowledge = {
            "extracted": {
                "quests": 3,
                "npcs": 5,
                "locations": 2,
            }
        }

        result = format_statistics_markdown(stats, knowledge)

        assert "Quests: 3" in result
        assert "Npcs: 5" in result
        assert "Locations: 2" in result

    def test_format_empty_stats(self):
        """Test formatting with no statistics."""
        result = format_statistics_markdown({}, {})

        assert "No statistics available" in result

    def test_format_with_fallback_duration(self):
        """Test formatting uses fallback when formatted duration missing."""
        stats = {
            "total_duration_seconds": 3665,
            "total_segments": 10,
        }

        result = format_statistics_markdown(stats, {})

        assert "3665 seconds" in result


class TestFormatSnippetExportMarkdown:
    """Test snippet export formatting."""

    def test_format_with_complete_snippet_data(self):
        """Test formatting with complete snippet export data."""
        snippet = {
            "manifest": "/path/to/manifest.json",
            "segments_dir": "/path/to/segments",
        }

        result = format_snippet_export_markdown(snippet)

        assert "/path/to/segments" in result
        assert "/path/to/manifest.json" in result

    def test_format_empty_snippet(self):
        """Test formatting with no snippet data."""
        result = format_snippet_export_markdown({})

        assert "disabled" in result.lower()

    def test_format_snippet_with_only_directory(self):
        """Test formatting with only segments directory."""
        snippet = {
            "segments_dir": "/path/to/segments",
        }

        result = format_snippet_export_markdown(snippet)

        assert "/path/to/segments" in result


class TestFormatPartyDisplay:
    """Test party display formatting."""

    def test_format_with_valid_party(self):
        """Test formatting with valid party."""
        mock_party = Mock()
        mock_party.party_name = "The Fellowship"
        mock_char1 = Mock()
        mock_char1.name = "Gandalf"
        mock_char1.class_name = "Wizard"
        mock_char2 = Mock()
        mock_char2.name = "Aragorn"
        mock_char2.class_name = "Ranger"
        mock_party.characters = [mock_char1, mock_char2]

        with patch('src.ui.process_session_helpers.PartyConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.get_party.return_value = mock_party
            mock_manager_class.return_value = mock_manager

            markdown, visible = format_party_display("fellowship_party")

        assert "The Fellowship" in markdown
        assert "Gandalf (Wizard)" in markdown
        assert "Aragorn (Ranger)" in markdown
        assert visible is True

    def test_format_with_manual_entry(self):
        """Test formatting returns empty for Manual Entry."""
        markdown, visible = format_party_display("Manual Entry")

        assert markdown == ""
        assert visible is False

    def test_format_with_nonexistent_party(self):
        """Test formatting returns empty for nonexistent party."""
        with patch('src.ui.process_session_helpers.PartyConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.get_party.return_value = None
            mock_manager_class.return_value = mock_manager

            markdown, visible = format_party_display("nonexistent")

        assert markdown == ""
        assert visible is False


class TestRenderProcessingResponse:
    """Test response rendering."""

    def test_success_response(self):
        """Test rendering successful response."""
        response = {
            "status": "success",
            "message": "Processed successfully",
            "full": "Full transcript",
            "ic": "IC transcript",
            "ooc": "OOC transcript",
            "stats": {"total_segments": 10},
            "snippet": {},
            "knowledge": {},
        }

        (
            status,
            visible,
            full_highlighted,
            full_plain,
            ic,
            ooc,
            stats,
            snippet,
            scroll,
            cancel_btn,
        ) = render_processing_response(response)

        assert "success" in status.lower()
        assert full_highlighted == []
        assert full_plain == "Full transcript"
        assert ic == "IC transcript"
        assert ooc == "OOC transcript"

    def test_error_response(self):
        """Test rendering error response."""
        response = {
            "status": "error",
            "message": "Processing failed",
            "details": "File not found",
        }

        (
            status,
            visible,
            full_highlighted,
            full_plain,
            ic,
            ooc,
            stats,
            snippet,
            scroll,
            cancel_btn,
        ) = render_processing_response(response)

        assert "failed" in status.lower()
        assert "File not found" in status

    def test_invalid_response_type(self):
        """Test rendering with invalid response type."""
        response = "not a dict"

        (
            status,
            visible,
            full_highlighted,
            full_plain,
            ic,
            ooc,
            stats,
            snippet,
            scroll,
            cancel_btn,
        ) = render_processing_response(response)

        assert "unexpected response" in status.lower()

    def test_response_includes_scroll_js(self):
        """Test that successful response includes scroll JavaScript."""
        response = {
            "status": "success",
            "message": "Done",
            "stats": {},
            "snippet": {},
            "knowledge": {},
        }

        (
            status,
            visible,
            full_highlighted,
            full_plain,
            ic,
            ooc,
            stats,
            snippet,
            scroll,
            cancel_btn,
        ) = render_processing_response(response)

        # scroll should be a gr.update with JavaScript
        assert scroll is not None


class TestPrepareProcessingStatus:
    """Test processing status preparation."""

    def test_prepare_with_valid_inputs(self):
        """Test preparation with valid inputs."""
        audio_file = Mock()
        audio_file.name = "/path/to/test.wav"

        with patch('pathlib.Path.exists', return_value=True):
            (status, results_update, should_proceed, log_clear, cancel_btn) = prepare_processing_status(
                audio_file=audio_file,
                session_id="session_001",
                party_selection="Manual Entry",
                character_names="Gandalf",
                player_names="",
                num_speakers=4,
            )

        assert should_proceed is True
        assert "processing" in status.lower()
        assert log_clear == ""

    def test_prepare_with_validation_errors(self):
        """Test preparation with validation errors."""
        (status, results_update, should_proceed, log_clear, cancel_btn) = prepare_processing_status(
            audio_file=None,
            session_id="",
            party_selection="Manual Entry",
            character_names="",
            player_names="",
            num_speakers=1,
        )

        assert should_proceed is False
        assert "validation failed" in status.lower()
        assert log_clear == ""


class TestPollTranscriptionProgress:
    """Test transcription progress polling."""

    @patch('src.ui.process_session_helpers.StatusTracker')
    def test_poll_with_active_transcription(self, mock_tracker):
        """Test polling with active transcription."""
        mock_tracker.get_snapshot.return_value = {
            "processing": True,
            "session_id": "session_001",
            "stages": [
                {
                    "id": 3,
                    "details": {
                        "last_chunk_preview": "This is a test transcript",
                        "chunks_transcribed": 5,
                        "total_chunks": 10,
                        "progress_percent": 50,
                        "last_chunk_index": 5,
                        "last_chunk_start": 0.0,
                        "last_chunk_end": 10.5,
                        "last_chunk_duration": 10.5,
                    }
                }
            ]
        }

        result = poll_transcription_progress("session_001")

        # Result should be a gr.update with markdown content
        assert result is not None

    @patch('src.ui.process_session_helpers.StatusTracker')
    def test_poll_with_no_processing(self, mock_tracker):
        """Test polling when no processing active."""
        mock_tracker.get_snapshot.return_value = {
            "processing": False,
        }

        result = poll_transcription_progress("session_001")

        # Should return empty update
        assert result is not None

    @patch('src.ui.process_session_helpers.StatusTracker')
    def test_poll_with_different_session(self, mock_tracker):
        """Test polling when session ID doesn't match."""
        mock_tracker.get_snapshot.return_value = {
            "processing": True,
            "session_id": "session_002",
            "stages": []
        }

        result = poll_transcription_progress("session_001")

        # Should return empty update
        assert result is not None


class TestPollRuntimeUpdates:
    """Test runtime updates polling."""

    @patch('src.ui.process_session_helpers.StatusTracker')
    def test_poll_with_active_processing(self, mock_tracker):
        """Test polling with active processing."""
        mock_tracker.get_snapshot.return_value = {
            "processing": True,
            "session_id": "session_001",
            "stages": [
                {
                    "id": 1,
                    "name": "Audio Loading",
                    "state": "completed",
                    "message": "Audio loaded",
                    "duration_seconds": 2.5,
                }
            ],
            "events": [
                {
                    "timestamp": "2025-01-11 10:30:00",
                    "type": "info",
                    "message": "Started processing",
                }
            ]
        }

        (stage_update, updated_log) = poll_runtime_updates("session_001", "")

        # Should return stage progress and updated log
        assert stage_update is not None
        assert "Started processing" in updated_log

    @patch('src.ui.process_session_helpers.StatusTracker')
    def test_poll_avoids_duplicate_events(self, mock_tracker):
        """Test polling doesn't duplicate existing log events."""
        mock_tracker.get_snapshot.return_value = {
            "processing": True,
            "session_id": "session_001",
            "stages": [],
            "events": [
                {
                    "timestamp": "2025-01-11 10:30:00",
                    "type": "info",
                    "message": "Event 1",
                },
                {
                    "timestamp": "2025-01-11 10:30:05",
                    "type": "info",
                    "message": "Event 2",
                }
            ]
        }

        existing_log = "[2025-01-11 10:30:00] ℹ Event 1"

        (stage_update, updated_log) = poll_runtime_updates("session_001", existing_log)

        # Should only add Event 2
        assert "Event 1" in updated_log
        assert "Event 2" in updated_log
        assert updated_log.count("Event 1") == 1  # Not duplicated


class TestPollOverallProgress:
    """Test overall progress polling and timing summaries."""

    @patch('src.ui.process_session_helpers._utcnow')
    @patch('src.ui.process_session_helpers.StatusTracker')
    def test_progress_includes_elapsed_eta_and_next_stage(self, mock_tracker, mock_now):
        """Progress display should surface timing and next stage hints."""

        mock_now.return_value = datetime(2025, 1, 1, 0, 2, 0)
        mock_tracker.get_snapshot.return_value = {
            "processing": True,
            "session_id": "session_001",
            "current_stage": 2,
            "started_at": "2025-01-01T00:00:00Z",
            "stages": [
                {"id": 1, "name": "Audio Conversion", "state": "completed", "duration_seconds": 30},
                {"id": 2, "name": "Chunking", "state": "running", "started_at": "2025-01-01T00:01:00Z"},
                {"id": 3, "name": "Transcription", "state": "pending"},
            ],
        }

        result = poll_overall_progress("session_001")

        assert result["visible"] is True
        assert "Elapsed:" in result["value"]
        assert "ETA:" in result["value"]
        assert "Next: Transcription" in result["value"]

    @patch('src.ui.process_session_helpers.StatusTracker')
    def test_progress_hidden_for_other_session(self, mock_tracker):
        """Hide progress when polling for a different session."""

        mock_tracker.get_snapshot.return_value = {
            "processing": True,
            "session_id": "session_002",
            "current_stage": 1,
            "stages": [],
        }

        result = poll_overall_progress("session_001")

        assert result["visible"] is False


class TestCheckFileProcessingHistory:
    """Test file history checking."""

    @patch('src.ui.process_session_helpers.FileProcessingTracker')
    def test_new_file_no_warning(self, mock_tracker_class):
        """Test that new files don't show warning."""
        mock_tracker = Mock()
        mock_tracker.check_file.return_value = None
        mock_tracker_class.return_value = mock_tracker

        file = Mock()
        file.name = "/path/to/test.wav"

        with patch('pathlib.Path.exists', return_value=True):
            warning, visible = check_file_processing_history(file)

        assert warning == ""
        assert visible is False

    @patch('src.ui.process_session_helpers.FileProcessingTracker')
    def test_previously_processed_file(self, mock_tracker_class):
        """Test that previously processed files show warning."""
        existing_record = Mock()
        existing_record.last_processed = datetime.now().isoformat()
        existing_record.session_id = "old_session"
        existing_record.process_count = 2
        existing_record.processing_stage = "completed"
        existing_record.status = "success"

        mock_tracker = Mock()
        mock_tracker.check_file.return_value = existing_record
        mock_tracker_class.return_value = mock_tracker

        file = Mock()
        file.name = "/path/to/test.wav"

        with patch('pathlib.Path.exists', return_value=True):
            warning, visible = check_file_processing_history(file)

        assert "Previously Processed" in warning
        assert "old_session" in warning
        assert visible is True

    def test_no_file_provided(self):
        """Test with no file provided."""
        warning, visible = check_file_processing_history(None)

        assert warning == ""
        assert visible is False

    @patch('src.ui.process_session_helpers.FileProcessingTracker')
    def test_file_does_not_exist(self, mock_tracker_class):
        """Test with file that doesn't exist on disk."""
        file = Mock()
        file.name = "/path/to/nonexistent.wav"

        with patch('pathlib.Path.exists', return_value=False):
            warning, visible = check_file_processing_history(file)

        assert warning == ""
        assert visible is False


class TestUpdatePartyDisplay:
    """Test party display update."""

    def test_update_with_valid_party(self):
        """Test updating display with valid party."""
        mock_party = Mock()
        mock_party.party_name = "The Fellowship"
        mock_char1 = Mock()
        mock_char1.name = "Gandalf"
        mock_char1.class_name = "Wizard"
        mock_party.characters = [mock_char1]

        with patch('src.ui.process_session_helpers.PartyConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.get_party.return_value = mock_party
            mock_manager_class.return_value = mock_manager

            result = update_party_display("fellowship_party")

        # Should return a gr.update
        assert result is not None

    def test_update_with_manual_entry(self):
        """Test updating display with Manual Entry."""
        result = update_party_display("Manual Entry")

        # Should return empty/hidden update
        assert result is not None


class TestValidateSessionIdRealtime:
    """Test real-time session ID validation for immediate UI feedback."""

    def test_valid_session_id(self):
        """A valid session ID should return a success message."""
        result = validate_session_id_realtime("valid_session-123")
        assert "Valid" in result
        assert "[v]" in result
        assert "`valid_session-123`" in result

    def test_invalid_characters(self):
        """An invalid session ID with special characters should show a detailed error."""
        result = validate_session_id_realtime("invalid session!")
        assert "Invalid Session ID" in result
        assert "[x]" in result
        assert "' '" in result
        assert "'!'" in result

    def test_invalid_unicode_characters(self):
        """Unicode characters that are not letters or numbers should be flagged as invalid."""
        result = validate_session_id_realtime("session-é-à")
        assert "Invalid Session ID" in result
        assert "[x]" in result
        assert "'é'" in result
        assert "'à'" in result

    def test_empty_session_id(self):
        """An empty string should return no message."""
        result = validate_session_id_realtime("")
        assert result == ""

    def test_whitespace_session_id(self):
        """A session ID with only whitespace should return no message."""
        result = validate_session_id_realtime("   ")
        assert result == ""

    @patch('src.ui.process_session_helpers.SessionManager')
    def test_duplicate_session_id(self, mock_session_manager):
        """A session ID that already exists should return a warning."""
        # This test ensures the core functionality of UX-04, preventing overwrites.
        mock_instance = mock_session_manager.return_value
        mock_session = MagicMock()
        mock_session.session_id = "existing_session"
        mock_instance.discover_sessions.return_value = [mock_session]

        # Invalidate the cache by resetting its timestamp
        from src.ui import process_session_helpers
        process_session_helpers._session_id_cache["timestamp"] = None

        result = validate_session_id_realtime("existing_session")

        assert "Duplicate Session ID" in result
        assert "`existing_session` already exists" in result

    @patch('src.ui.process_session_helpers.SessionManager')
    def test_session_id_caching_behavior(self, mock_session_manager):
        """Test that the session ID cache is used to prevent excessive I/O."""
        # Why this test is important:
        # This test directly addresses the performance feedback from the code
        # review. It ensures that the caching mechanism works, preventing the
        # expensive `discover_sessions` call from running on every keystroke,
        # which would cause UI lag.

        # Arrange: Mock the SessionManager.
        mock_instance = mock_session_manager.return_value
        mock_session = MagicMock()
        mock_session.session_id = "cached_session"
        mock_instance.discover_sessions.return_value = [mock_session]

        # Invalidate the cache to ensure the first call hits the mock.
        from src.ui import process_session_helpers
        process_session_helpers._session_id_cache["timestamp"] = None

        # Act 1: First call should populate the cache.
        validate_session_id_realtime("cached_session")

        # Assert 1: The mock should have been called once.
        mock_instance.discover_sessions.assert_called_once()

        # Act 2: Second call should use the cache, not the mock.
        validate_session_id_realtime("cached_session")

        # Assert 2: The mock call count should still be one.
        mock_instance.discover_sessions.assert_called_once()

    def test_update_with_nonexistent_party(self):
        """Test updating display with nonexistent party."""
        with patch('src.ui.process_session_helpers.PartyConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.get_party.return_value = None
            mock_manager_class.return_value = mock_manager

            result = update_party_display("nonexistent")

        # Should return empty/hidden update
        assert result is not None
