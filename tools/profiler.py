"""Pipeline profiling utilities using cProfile.

This module provides a CLI for profiling the full DDSessionProcessor
execution path. It saves cProfile stats to a file for later inspection
with tools like snakeviz and prints a short console summary of the top
functions by cumulative time.
"""

from __future__ import annotations

import argparse
import cProfile
import io
import pstats
from pathlib import Path
from typing import Callable, Optional, Sequence, Tuple

from src.pipeline import DDSessionProcessor

DEFAULT_PROFILE_PATH = Path("profiles") / "pipeline.prof"
DEFAULT_SUMMARY_COUNT = 30


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments for the profiler CLI."""
    parser = argparse.ArgumentParser(description="Profile the session pipeline with cProfile.")
    parser.add_argument("--input", required=True, type=Path, help="Path to an input audio or video file.")
    parser.add_argument("--session-id", type=str, help="Optional session identifier. Defaults to the input filename.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_PROFILE_PATH,
        help="Destination for the .prof stats file (directories will be created).",
    )
    parser.add_argument("--party", type=str, help="Party configuration to use when instantiating the pipeline.")
    parser.add_argument("--num-speakers", type=int, default=4, help="Expected number of speakers.")
    parser.add_argument("--skip-diarization", action="store_true", help="Skip speaker diarization stage.")
    parser.add_argument("--skip-classification", action="store_true", help="Skip IC/OOC classification stage.")
    parser.add_argument("--skip-snippets", action="store_true", help="Skip snippet export stage.")
    parser.add_argument("--skip-knowledge", action="store_true", help="Skip knowledge extraction stage.")
    parser.add_argument(
        "--summary-count",
        type=int,
        default=DEFAULT_SUMMARY_COUNT,
        help="Number of rows to include in the console summary output.",
    )
    return parser.parse_args(argv)


def normalize_paths(input_path: Path, output_path: Path) -> Tuple[Path, Path]:
    """Resolve input and output paths and ensure the output directory exists."""
    resolved_input = input_path.expanduser().resolve()
    if not resolved_input.exists():
        raise FileNotFoundError(f"Input file not found: {resolved_input}")

    resolved_output = output_path.expanduser()
    if not resolved_output.is_absolute():
        resolved_output = Path.cwd() / resolved_output

    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    return resolved_input, resolved_output


def build_processor(options: argparse.Namespace) -> DDSessionProcessor:
    """Construct a DDSessionProcessor based on the provided options."""
    session_id = options.session_id or options.input.stem
    return DDSessionProcessor(
        session_id=session_id,
        num_speakers=options.num_speakers,
        party_id=options.party,
    )


def run_pipeline(options: argparse.Namespace) -> None:
    """Execute the pipeline with the given options."""
    processor = build_processor(options)
    processor.process(
        input_file=options.input,
        skip_diarization=options.skip_diarization,
        skip_classification=options.skip_classification,
        skip_snippets=options.skip_snippets,
        skip_knowledge=options.skip_knowledge,
    )


def format_stats(stats: pstats.Stats, limit: int) -> str:
    """Render a cumulative time summary for console output."""
    buffer = io.StringIO()
    stats.stream = buffer
    stats.sort_stats("cumulative").print_stats(limit)
    return buffer.getvalue()


def profile_pipeline(
    options: argparse.Namespace,
    runner: Callable[[argparse.Namespace], None] = run_pipeline,
) -> Tuple[Path, pstats.Stats]:
    """Profile the pipeline runner and return the stats object and output path."""
    options.input, options.output = normalize_paths(options.input, options.output)
    profile = cProfile.Profile()
    profile.runcall(runner, options)
    profile.dump_stats(options.output)
    stats = pstats.Stats(profile)
    return options.output, stats


def main(argv: Optional[Sequence[str]] = None) -> None:
    options = parse_args(argv)
    output_path, stats = profile_pipeline(options)
    summary = format_stats(stats, options.summary_count)
    print(f"Profile saved to: {output_path}")
    print("\nTop functions by cumulative time:\n")
    print(summary)


if __name__ == "__main__":
    main()
