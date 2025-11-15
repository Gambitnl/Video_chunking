#!/usr/bin/env python
"""
CLI tool to process D&D sessions from intermediate stage outputs.

This tool allows you to:
1. Load intermediate outputs from a previous processing run
2. Resume processing from a specific stage
3. Skip earlier stages that have already been completed

Usage:
    # Continue from merged transcript (run diarization, classification, output generation)
    python process_from_intermediate.py --session-dir output/20251115_120000_session --from-stage 4

    # Continue from diarization (run classification and output generation)
    python process_from_intermediate.py --session-dir output/20251115_120000_session --from-stage 5

    # Continue from classification (regenerate outputs only)
    python process_from_intermediate.py --session-dir output/20251115_120000_session --from-stage 6
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from src.config import Config
from src.intermediate_output import IntermediateOutputManager
from src.pipeline import DDSessionProcessor
from src.logger import setup_logging, get_logger

logger = logging.getLogger("process_from_intermediate")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Process D&D sessions from intermediate stage outputs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--session-dir",
        type=str,
        required=True,
        help="Path to the session output directory (e.g., output/20251115_120000_session)",
    )

    parser.add_argument(
        "--from-stage",
        type=int,
        required=True,
        choices=[4, 5, 6],
        help="Stage number to resume from (4=transcript, 5=diarization, 6=classification)",
    )

    parser.add_argument(
        "--skip-diarization",
        action="store_true",
        help="Skip speaker diarization (use UNKNOWN speaker labels)",
    )

    parser.add_argument(
        "--skip-classification",
        action="store_true",
        help="Skip IC/OOC classification (treat all segments as IC)",
    )

    parser.add_argument(
        "--skip-snippets",
        action="store_true",
        help="Skip audio segment export",
    )

    parser.add_argument(
        "--skip-knowledge",
        action="store_true",
        help="Skip knowledge extraction",
    )

    parser.add_argument(
        "--party-id",
        type=str,
        help="Party configuration ID to use",
    )

    parser.add_argument(
        "--campaign-id",
        type=str,
        help="Campaign identifier",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )

    return parser.parse_args()


def load_intermediate_output(
    manager: IntermediateOutputManager,
    stage: int,
) -> tuple:
    """
    Load intermediate output for the specified stage.

    Args:
        manager: IntermediateOutputManager instance
        stage: Stage number to load (4, 5, or 6)

    Returns:
        Tuple containing the loaded data appropriate for the stage

    Raises:
        FileNotFoundError: If the intermediate output file doesn't exist
        ValueError: If the file format is invalid
    """
    if stage == 4:
        logger.info("Loading merged transcript from intermediate output...")
        merged_segments = manager.load_merged_transcript()
        logger.info("Loaded %d merged segments", len(merged_segments))
        return (merged_segments,)

    elif stage == 5:
        logger.info("Loading diarization output from intermediate output...")
        speaker_segments = manager.load_diarization()
        logger.info("Loaded %d speaker-labeled segments", len(speaker_segments))
        return (speaker_segments,)

    elif stage == 6:
        logger.info("Loading classification output from intermediate output...")
        segments, classifications = manager.load_classification()
        logger.info("Loaded %d classified segments", len(segments))
        return (segments, classifications)

    else:
        raise ValueError(f"Invalid stage number: {stage}")


def process_from_stage(args):
    """
    Process a session starting from an intermediate stage.

    Args:
        args: Parsed command line arguments

    Returns:
        0 on success, 1 on failure
    """
    session_dir = Path(args.session_dir)

    # Validate session directory
    if not session_dir.exists():
        logger.error("Session directory does not exist: %s", session_dir)
        return 1

    if not session_dir.is_dir():
        logger.error("Path is not a directory: %s", session_dir)
        return 1

    # Initialize intermediate output manager
    manager = IntermediateOutputManager(session_dir)

    # Check if intermediate output exists
    if not manager.stage_output_exists(args.from_stage):
        logger.error(
            "Intermediate output for stage %d not found in %s",
            args.from_stage,
            manager.intermediates_dir,
        )
        logger.error(
            "Expected file: %s",
            manager.get_stage_path(args.from_stage),
        )
        logger.error(
            "\nMake sure you've run a session with SAVE_INTERMEDIATE_OUTPUTS=true, "
            "or check the session directory path."
        )
        return 1

    # Load intermediate output
    try:
        loaded_data = load_intermediate_output(manager, args.from_stage)
    except Exception as e:
        logger.error("Failed to load intermediate output: %s", e)
        return 1

    # Extract session ID from directory name
    session_id = session_dir.name.split("_", 2)[-1]  # Get part after timestamp

    logger.info("=" * 80)
    logger.info("Processing session '%s' from stage %d", session_id, args.from_stage)
    logger.info("Session directory: %s", session_dir)
    logger.info("=" * 80)

    # Initialize pipeline
    processor = DDSessionProcessor(
        session_id=session_id,
        campaign_id=args.campaign_id,
        party_id=args.party_id,
        resume=False,  # Disable checkpointing for manual processing
    )

    # Process from intermediate stage
    try:
        result = processor.process_from_intermediate(
            session_dir=session_dir,
            from_stage=args.from_stage,
            skip_diarization=args.skip_diarization,
            skip_classification=args.skip_classification,
            skip_snippets=args.skip_snippets,
            skip_knowledge=args.skip_knowledge,
        )

        if result['success']:
            logger.info("=" * 80)
            logger.info("Processing completed successfully!")
            logger.info("=" * 80)

            # Display output files
            logger.info("\nOutput files:")
            for format_name, file_path in result['output_files'].items():
                logger.info("  %s: %s", format_name, file_path)

            # Display statistics
            if result['statistics']:
                stats = result['statistics']
                logger.info("\nStatistics:")
                logger.info("  Total duration: %s", stats.get('total_duration_formatted', 'N/A'))
                logger.info("  IC duration: %s (%.1f%%)",
                           stats.get('ic_duration_formatted', 'N/A'),
                           stats.get('ic_percentage', 0.0))
                logger.info("  Total segments: %d", stats.get('total_segments', 0))
                logger.info("  IC segments: %d", stats.get('ic_segments', 0))
                logger.info("  OOC segments: %d", stats.get('ooc_segments', 0))

            # Display knowledge extraction results
            if result['knowledge_extraction']:
                knowledge = result['knowledge_extraction']
                logger.info("\nKnowledge extraction:")
                logger.info("  Total entities: %d", knowledge.get('total_entities', 0))

            return 0
        else:
            logger.error("Processing failed")
            return 1

    except Exception as e:
        logger.error("Processing failed: %s", e)
        return 1


def main():
    """Main entry point."""
    args = parse_args()

    # Setup logging
    setup_logging()
    logger.setLevel(getattr(logging, args.log_level))

    # Process from intermediate stage
    try:
        exit_code = process_from_stage(args)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
