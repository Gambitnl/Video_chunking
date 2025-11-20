from pathlib import Path

import pytest

from tools.profiler import (
    DEFAULT_PROFILE_PATH,
    DEFAULT_SUMMARY_COUNT,
    format_stats,
    normalize_paths,
    parse_args,
    profile_pipeline,
)


def test_parse_args_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "session.m4a"
    input_path.write_bytes(b"test")

    args = parse_args(["--input", str(input_path)])

    assert args.input == input_path
    assert args.output == DEFAULT_PROFILE_PATH
    assert args.summary_count == DEFAULT_SUMMARY_COUNT
    assert args.session_id is None


def test_normalize_paths_creates_output_dir(tmp_path):
    input_path = tmp_path / "audio.wav"
    input_path.write_bytes(b"audio")
    output_path = tmp_path / "profiles" / "custom.prof"

    resolved_input, resolved_output = normalize_paths(input_path, output_path)

    assert resolved_input == input_path.resolve()
    assert resolved_output == output_path
    assert resolved_output.parent.exists()


def test_profile_pipeline_writes_stats(tmp_path):
    input_path = tmp_path / "example.wav"
    input_path.write_bytes(b"audio")
    output_path = tmp_path / "stats.prof"

    args = parse_args(["--input", str(input_path), "--output", str(output_path)])

    def runner(options):
        # Perform some work so the profile has entries.
        total = 0
        for value in range(100):
            total += value
        assert options.input.exists()
        return total

    profile_path, stats = profile_pipeline(args, runner=runner)

    assert profile_path == output_path
    assert profile_path.exists()

    summary = format_stats(stats, limit=5)
    assert "runner" in summary


def test_normalize_paths_raises_for_missing_input(tmp_path):
    missing_input = tmp_path / "missing.wav"
    with pytest.raises(FileNotFoundError):
        normalize_paths(missing_input, tmp_path / "profile.prof")
