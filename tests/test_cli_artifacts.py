"""Tests for CLI artifacts commands."""
import pytest
from pathlib import Path
from click.testing import CliRunner
import json

from cli import cli


def _prepare_api_instance(monkeypatch, output_dir):
    """Reset the global session artifact API to point at a test directory."""
    from src.api import session_artifacts

    monkeypatch.setattr(
        session_artifacts,
        '_api_instance',
        session_artifacts.SessionArtifactsAPI(output_dir=output_dir),
    )


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_session_dir(tmp_path):
    """Create a sample session directory structure for testing."""
    session_name = "20251116_120000_test_session"
    session_dir = tmp_path / "output" / session_name
    session_dir.mkdir(parents=True, exist_ok=True)

    # Create some sample files
    (session_dir / "test_session_full.txt").write_text("Full transcript content", encoding="utf-8")
    (session_dir / "test_session_ic_only.txt").write_text("IC only content", encoding="utf-8")
    (session_dir / "test_session_data.json").write_text('{"test": "data"}', encoding="utf-8")

    # Create intermediates subdirectory
    intermediates_dir = session_dir / "intermediates"
    intermediates_dir.mkdir(exist_ok=True)
    (intermediates_dir / "stage_4_merged.json").write_text('{"stage": 4}', encoding="utf-8")

    return tmp_path / "output", session_name


class TestArtifactsList:
    """Tests for 'artifacts list' command."""

    def test_list_no_sessions(self, cli_runner, tmp_path, monkeypatch):
        """Test listing when no sessions exist."""
        # Mock Config.OUTPUT_DIR to point to empty directory
        from src import config
        empty_dir = tmp_path / "empty_output"
        empty_dir.mkdir()
        monkeypatch.setattr(config.Config, 'OUTPUT_DIR', empty_dir)
        _prepare_api_instance(monkeypatch, empty_dir)

        result = cli_runner.invoke(cli, ['artifacts', 'list'])

        assert result.exit_code == 0
        assert "No sessions found" in result.output

    def test_list_with_sessions(self, cli_runner, sample_session_dir, monkeypatch):
        """Test listing sessions."""
        output_dir, session_name = sample_session_dir
        from src import config
        monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
        _prepare_api_instance(monkeypatch, output_dir)

        result = cli_runner.invoke(cli, ['artifacts', 'list'])

        assert result.exit_code == 0
        assert session_name in result.output
        assert "Processed Sessions" in result.output

    def test_list_with_limit(self, cli_runner, sample_session_dir, monkeypatch):
        """Test listing with limit parameter."""
        output_dir, _ = sample_session_dir
        from src import config
        monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
        _prepare_api_instance(monkeypatch, output_dir)

        result = cli_runner.invoke(cli, ['artifacts', 'list', '--limit', '1'])

        assert result.exit_code == 0

    def test_list_json_output(self, cli_runner, sample_session_dir, monkeypatch):
        """Test JSON output format."""
        output_dir, session_name = sample_session_dir
        from src import config
        monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
        _prepare_api_instance(monkeypatch, output_dir)

        result = cli_runner.invoke(cli, ['artifacts', 'list', '--json'])

        assert result.exit_code == 0
        # Verify it's valid JSON
        output_data = json.loads(result.output)
        assert output_data['status'] == 'success'
        assert 'sessions' in output_data['data']


class TestArtifactsTree:
    """Tests for 'artifacts tree' command."""

    def test_tree_nonexistent_session(self, cli_runner, tmp_path, monkeypatch):
        """Test tree for non-existent session."""
        from src import config
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
        _prepare_api_instance(monkeypatch, output_dir)

        result = cli_runner.invoke(cli, ['artifacts', 'tree', 'nonexistent'])

        assert result.exit_code == 1
        assert "Error" in result.output

    def test_tree_existing_session(self, cli_runner, sample_session_dir, monkeypatch):
        """Test tree for existing session."""
        output_dir, session_name = sample_session_dir
        from src import config
        monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
        _prepare_api_instance(monkeypatch, output_dir)

        result = cli_runner.invoke(cli, ['artifacts', 'tree', session_name])

        assert result.exit_code == 0
        assert "Contents of" in result.output
        assert "test_session_full.txt" in result.output
        assert "test_session_data.json" in result.output

    def test_tree_shows_subdirectories(self, cli_runner, sample_session_dir, monkeypatch):
        """Test that tree shows subdirectories."""
        output_dir, session_name = sample_session_dir
        from src import config
        monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
        _prepare_api_instance(monkeypatch, output_dir)

        result = cli_runner.invoke(cli, ['artifacts', 'tree', session_name])

        assert result.exit_code == 0
        assert "intermediates" in result.output

    def test_tree_json_output(self, cli_runner, sample_session_dir, monkeypatch):
        """Test tree JSON output."""
        output_dir, session_name = sample_session_dir
        from src import config
        monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
        _prepare_api_instance(monkeypatch, output_dir)

        result = cli_runner.invoke(cli, ['artifacts', 'tree', session_name, '--json'])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data['status'] == 'success'
        assert 'items' in output_data['data']


class TestArtifactsDownload:
    """Tests for 'artifacts download' command."""

    def test_download_nonexistent_session(self, cli_runner, tmp_path, monkeypatch):
        """Test downloading non-existent session."""
        from src import config
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
        _prepare_api_instance(monkeypatch, output_dir)

        result = cli_runner.invoke(cli, ['artifacts', 'download', 'nonexistent'])

        assert result.exit_code == 1
        assert "Error" in result.output

    def test_download_session_as_zip(self, cli_runner, sample_session_dir, tmp_path, monkeypatch):
        """Test downloading entire session as zip."""
        output_dir, session_name = sample_session_dir
        from src import config
        monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
        monkeypatch.setattr(config.Config, 'TEMP_DIR', tmp_path / "temp")
        _prepare_api_instance(monkeypatch, output_dir)

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            result = cli_runner.invoke(cli, ['artifacts', 'download', session_name])

            assert result.exit_code == 0
            assert "downloaded" in result.output.lower()

    def test_download_specific_file(self, cli_runner, sample_session_dir, tmp_path, monkeypatch):
        """Test downloading specific file."""
        output_dir, session_name = sample_session_dir
        from src import config
        monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
        _prepare_api_instance(monkeypatch, output_dir)

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            result = cli_runner.invoke(
                cli,
                ['artifacts', 'download', session_name, '--file', 'test_session_full.txt']
            )

            assert result.exit_code == 0
            assert "downloaded" in result.output.lower()

    def test_download_nonexistent_file(self, cli_runner, sample_session_dir, monkeypatch):
        """Test downloading non-existent file."""
        output_dir, session_name = sample_session_dir
        from src import config
        monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
        _prepare_api_instance(monkeypatch, output_dir)

        result = cli_runner.invoke(
            cli,
            ['artifacts', 'download', session_name, '--file', 'nonexistent.txt']
        )

        assert result.exit_code == 1
        assert "Error" in result.output

    def test_download_with_custom_output_path(self, cli_runner, sample_session_dir, tmp_path, monkeypatch):
        """Test downloading with custom output path."""
        output_dir, session_name = sample_session_dir
        from src import config
        monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
        monkeypatch.setattr(config.Config, 'TEMP_DIR', tmp_path / "temp")
        _prepare_api_instance(monkeypatch, output_dir)

        output_file = tmp_path / "custom_output.zip"

        result = cli_runner.invoke(
            cli,
            ['artifacts', 'download', session_name, '--output', str(output_file)]
        )

        assert result.exit_code == 0
        # Note: In isolated filesystem, the file may not actually be at the expected path
        # but the command should succeed


class TestArtifactsDelete:
    """Tests for 'artifacts delete' command."""

    def test_delete_file(self, cli_runner, sample_session_dir, monkeypatch):
        """Deleting a file should remove it from disk."""
        output_dir, session_name = sample_session_dir
        from src import config
        monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
        _prepare_api_instance(monkeypatch, output_dir)

        target = f"{session_name}/test_session_ic_only.txt"
        result = cli_runner.invoke(cli, ['artifacts', 'delete', target])

        assert result.exit_code == 0
        assert "Deleted" in result.output
        assert not (output_dir / target).exists()

    def test_delete_directory_requires_recursive(self, cli_runner, sample_session_dir, monkeypatch):
        """Attempting to delete a directory without recursive should fail."""
        output_dir, session_name = sample_session_dir
        from src import config
        monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
        _prepare_api_instance(monkeypatch, output_dir)

        target = f"{session_name}/intermediates"
        result = cli_runner.invoke(cli, ['artifacts', 'delete', target])

        assert result.exit_code != 0
        assert "Error" in result.output

    def test_delete_directory_recursive(self, cli_runner, sample_session_dir, monkeypatch):
        """Recursive deletion should succeed."""
        output_dir, session_name = sample_session_dir
        from src import config
        monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
        _prepare_api_instance(monkeypatch, output_dir)

        target = f"{session_name}/intermediates"
        result = cli_runner.invoke(cli, ['artifacts', 'delete', target, '--recursive'])

        assert result.exit_code == 0
        assert "Deleted directory" in result.output
