"""Tests for Session Artifacts API."""
import pytest
from pathlib import Path
import json

from src.api.session_artifacts import (
    SessionArtifactsAPI,
    list_sessions_api,
    get_directory_tree_api,
    get_artifact_metadata_api,
    get_file_preview_api,
    download_file_api,
    download_session_api,
    delete_artifact_api,
)


@pytest.fixture
def sample_session_structure(tmp_path):
    """Create a sample session directory structure for testing."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create session 1
    session1_name = "20251116_120000_session1"
    session1_dir = output_dir / session1_name
    session1_dir.mkdir()

    (session1_dir / "session1_full.txt").write_text("Full transcript", encoding="utf-8")
    (session1_dir / "session1_ic_only.txt").write_text("IC only", encoding="utf-8")
    (session1_dir / "session1_data.json").write_text(json.dumps({"test": "data"}), encoding="utf-8")

    # Create intermediates subdirectory
    intermediates = session1_dir / "intermediates"
    intermediates.mkdir()
    (intermediates / "stage_4.json").write_text(json.dumps({"stage": 4}), encoding="utf-8")

    # Create session 2 (older)
    session2_name = "20251115_110000_session2"
    session2_dir = output_dir / session2_name
    session2_dir.mkdir()
    (session2_dir / "session2_full.txt").write_text("Session 2 content", encoding="utf-8")

    return output_dir, session1_name, session2_name


@pytest.fixture
def api_instance(sample_session_structure):
    """Create API instance with sample data."""
    output_dir, _, _ = sample_session_structure
    return SessionArtifactsAPI(output_dir=output_dir)


class TestSessionArtifactsAPI:
    """Tests for SessionArtifactsAPI class."""

    def test_api_initialization(self, sample_session_structure):
        """Test API can be initialized."""
        output_dir, _, _ = sample_session_structure
        api = SessionArtifactsAPI(output_dir=output_dir)
        assert api.service.output_dir == output_dir

    def test_list_sessions_success(self, api_instance):
        """Test listing sessions returns success."""
        response = api_instance.list_sessions()

        assert response['status'] == 'success'
        assert 'sessions' in response['data']
        assert len(response['data']['sessions']) >= 2

    def test_list_sessions_sorted_by_modified(self, api_instance):
        """Test sessions are sorted by modification time (newest first)."""
        response = api_instance.list_sessions()

        sessions = response['data']['sessions']
        mods = [session['modified'] for session in sessions]

        from datetime import datetime
        parsed = [datetime.fromisoformat(ts) for ts in mods]
        assert parsed == sorted(parsed, reverse=True)

    def test_get_directory_tree_success(self, api_instance, sample_session_structure):
        """Test getting directory tree for a session."""
        _, session1_name, _ = sample_session_structure

        response = api_instance.get_directory_tree(session1_name)

        assert response['status'] == 'success'
        assert 'items' in response['data']
        items = response['data']['items']

        # Should have files and subdirectory
        assert len(items) >= 4  # 3 files + 1 subdirectory
        file_names = [item['name'] for item in items]
        assert 'session1_full.txt' in file_names
        assert 'intermediates' in file_names

    def test_get_directory_tree_nonexistent(self, api_instance):
        """Test getting tree for non-existent session."""
        response = api_instance.get_directory_tree("nonexistent_session")

        assert response['status'] in ('not_found', 'invalid')

    def test_get_artifact_metadata_success(self, api_instance, sample_session_structure):
        """Test getting metadata for specific artifact."""
        _, session1_name, _ = sample_session_structure

        response = api_instance.get_artifact_metadata(f"{session1_name}/session1_full.txt")

        assert response['status'] == 'success'
        assert response['data']['name'] == 'session1_full.txt'
        assert response['data']['artifact_type'] == 'txt'
        assert response['data']['is_directory'] is False

    def test_get_artifact_metadata_directory(self, api_instance, sample_session_structure):
        """Test getting metadata for directory."""
        _, session1_name, _ = sample_session_structure

        response = api_instance.get_artifact_metadata(f"{session1_name}/intermediates")

        assert response['status'] == 'success'
        assert response['data']['is_directory'] is True
        assert response['data']['artifact_type'] == 'directory'

    def test_get_file_preview_text_file(self, api_instance, sample_session_structure):
        """Test previewing text file."""
        _, session1_name, _ = sample_session_structure

        response = api_instance.get_file_preview(f"{session1_name}/session1_full.txt")

        assert response['status'] == 'success'
        assert response['data']['content'] == "Full transcript"
        assert response['data']['truncated'] is False
        assert response['data']['encoding'] == 'utf-8'

    def test_get_file_preview_json_file(self, api_instance, sample_session_structure):
        """Test previewing JSON file."""
        _, session1_name, _ = sample_session_structure

        response = api_instance.get_file_preview(f"{session1_name}/session1_data.json")

        assert response['status'] == 'success'
        content = response['data']['content']
        # Verify it's valid JSON
        data = json.loads(content)
        assert data['test'] == 'data'

    def test_get_file_preview_with_size_limit(self, api_instance, sample_session_structure):
        """Test preview with size limit causes truncation."""
        _, session1_name, _ = sample_session_structure

        # Create a file larger than the limit
        session_path = api_instance.service.output_dir / session1_name
        large_file = session_path / "large.txt"
        large_file.write_text("x" * 20000, encoding="utf-8")

        response = api_instance.get_file_preview(f"{session1_name}/large.txt", max_size_kb=5)

        assert response['status'] == 'success'
        assert response['data']['truncated'] is True
        assert len(response['data']['content']) <= 5 * 1024

    def test_get_file_preview_nonexistent(self, api_instance):
        """Test previewing non-existent file."""
        response = api_instance.get_file_preview("nonexistent/file.txt")

        assert response['status'] == 'not_found'

    def test_download_file_success(self, api_instance, sample_session_structure):
        """Test downloading a file."""
        _, session1_name, _ = sample_session_structure

        result = api_instance.download_file(f"{session1_name}/session1_full.txt")

        assert result is not None
        file_path, filename = result
        assert file_path.exists()
        assert filename == "session1_full.txt"

    def test_download_file_nonexistent(self, api_instance):
        """Test downloading non-existent file."""
        result = api_instance.download_file("nonexistent/file.txt")

        assert result is None

    def test_download_session_creates_zip(self, api_instance, sample_session_structure):
        """Test downloading entire session creates zip file."""
        _, session1_name, _ = sample_session_structure

        result = api_instance.download_session(session1_name)

        assert result is not None
        zip_path, filename = result
        assert zip_path.exists()
        assert filename.endswith('.zip')

    def test_download_session_nonexistent(self, api_instance):
        """Test downloading non-existent session."""
        result = api_instance.download_session("nonexistent_session")

        assert result is None

    def test_delete_artifact_file(self, api_instance, sample_session_structure):
        """Deleting a file should succeed and return metadata."""
        _, session1_name, _ = sample_session_structure
        target = f"{session1_name}/session1_full.txt"

        response = api_instance.delete_artifact(target)
        assert response["status"] == "success"
        assert response["data"]["relative_path"] == target

        # Subsequent metadata lookup should fail
        missing = api_instance.get_artifact_metadata(target)
        assert missing["status"] == "not_found"

    def test_delete_artifact_directory_requires_recursive(self, api_instance, sample_session_structure):
        """Deleting a directory without recursive flag should fail."""
        _, session1_name, _ = sample_session_structure
        response = api_instance.delete_artifact(f"{session1_name}/intermediates", recursive=False)
        assert response["status"] == "invalid"

    def test_delete_artifact_directory_recursive(self, api_instance, sample_session_structure):
        """Recursive deletion should allow directory removal."""
        _, session1_name, _ = sample_session_structure
        response = api_instance.delete_artifact(f"{session1_name}/intermediates", recursive=True)
        assert response["status"] == "success"

    def test_empty_session_id_validation(self, api_instance):
        """Test that empty session IDs are rejected."""
        response = api_instance.get_directory_tree("")

        assert response['status'] == 'invalid'
        assert 'required' in response['error'].lower()

    def test_response_format_consistency(self, api_instance):
        """Test all responses have consistent format."""
        response = api_instance.list_sessions()

        # Check standard fields
        assert 'status' in response
        assert 'data' in response
        assert 'error' in response
        assert 'timestamp' in response

        # Timestamp should be ISO format
        from datetime import datetime
        datetime.fromisoformat(response['timestamp'])


class TestConvenienceFunctions:
    """Tests for convenience wrapper functions."""

    def test_list_sessions_convenience(self, sample_session_structure, monkeypatch):
        """Test list_sessions_api convenience function."""
        output_dir, _, _ = sample_session_structure

        # Mock the global instance to use our test directory
        from src.api import session_artifacts
        monkeypatch.setattr(session_artifacts, '_api_instance', SessionArtifactsAPI(output_dir))

        response = list_sessions_api()

        assert response['status'] == 'success'
        assert len(response['data']['sessions']) >= 2

    def test_get_directory_tree_convenience(self, sample_session_structure, monkeypatch):
        """Test get_directory_tree_api convenience function."""
        output_dir, session1_name, _ = sample_session_structure

        from src.api import session_artifacts
        monkeypatch.setattr(session_artifacts, '_api_instance', SessionArtifactsAPI(output_dir))

        response = get_directory_tree_api(session1_name)

        assert response['status'] == 'success'

    def test_get_artifact_metadata_convenience(self, sample_session_structure, monkeypatch):
        """Test get_artifact_metadata_api convenience function."""
        output_dir, session1_name, _ = sample_session_structure

        from src.api import session_artifacts
        monkeypatch.setattr(session_artifacts, '_api_instance', SessionArtifactsAPI(output_dir))

        response = get_artifact_metadata_api(f"{session1_name}/session1_full.txt")

        assert response['status'] == 'success'

    def test_get_file_preview_convenience(self, sample_session_structure, monkeypatch):
        """Test get_file_preview_api convenience function."""
        output_dir, session1_name, _ = sample_session_structure

        from src.api import session_artifacts
        monkeypatch.setattr(session_artifacts, '_api_instance', SessionArtifactsAPI(output_dir))

        response = get_file_preview_api(f"{session1_name}/session1_full.txt")

        assert response['status'] == 'success'

    def test_download_file_convenience(self, sample_session_structure, monkeypatch):
        """Test download_file_api convenience function."""
        output_dir, session1_name, _ = sample_session_structure

        from src.api import session_artifacts
        monkeypatch.setattr(session_artifacts, '_api_instance', SessionArtifactsAPI(output_dir))

        result = download_file_api(f"{session1_name}/session1_full.txt")

        assert result is not None

    def test_download_session_convenience(self, sample_session_structure, monkeypatch):
        """Test download_session_api convenience function."""
        output_dir, session1_name, _ = sample_session_structure

        from src.api import session_artifacts
        monkeypatch.setattr(session_artifacts, '_api_instance', SessionArtifactsAPI(output_dir))

        result = download_session_api(session1_name)

        assert result is not None

    def test_delete_artifact_convenience(self, sample_session_structure, monkeypatch):
        """Test delete_artifact_api convenience function."""
        output_dir, session1_name, _ = sample_session_structure

        from src.api import session_artifacts
        monkeypatch.setattr(session_artifacts, '_api_instance', SessionArtifactsAPI(output_dir))

        response = delete_artifact_api(f"{session1_name}/session1_ic_only.txt")

        assert response["status"] == "success"


class TestPathSecurity:
    """Tests for path traversal security."""

    def test_path_traversal_blocked_in_tree(self, api_instance):
        """Test that path traversal attempts are blocked."""
        response = api_instance.get_directory_tree("../../../etc/passwd")

        assert response['status'] in ['not_found', 'invalid']

    def test_path_traversal_blocked_in_preview(self, api_instance):
        """Test that path traversal is blocked in preview."""
        response = api_instance.get_file_preview("../../etc/passwd")

        assert response['status'] in ['not_found', 'invalid']

    def test_absolute_path_rejected(self, api_instance, tmp_path):
        """Test that absolute paths are rejected."""
        # Create a file outside the output directory
        outside_file = tmp_path / "outside.txt"
        outside_file.write_text("Should not be accessible", encoding="utf-8")

        response = api_instance.get_file_preview(str(outside_file))

        assert response['status'] in ['not_found', 'invalid']
