"""
Test script for Colab Classifier using existing checkpoint data.

This script loads diarization results from a previous run and tests
the ColabClassifier without re-running the full pipeline.

Usage:
    python test_colab_classifier.py [--num-segments 20] [--checkpoint-dir test_s6_nov12_1111am]
"""

import gzip
import json
from pathlib import Path
import argparse
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.classifier import ClassifierFactory
from src.logger import get_logger

logger = get_logger(__name__)


def load_checkpoint_segments(checkpoint_dir: str, num_segments: int = 20):
    """
    Load speaker segments from checkpoint data.

    Args:
        checkpoint_dir: Name of checkpoint directory (e.g., 'test_s6_nov12_1111am')
        num_segments: Number of segments to load for testing

    Returns:
        List of segment dictionaries
    """
    base_path = Path("output/_checkpoints") / checkpoint_dir
    segments_file = base_path / "speaker_diarized_speaker_segments.json.gz"

    if not segments_file.exists():
        raise FileNotFoundError(f"Checkpoint file not found: {segments_file}")

    logger.info(f"Loading checkpoint from: {segments_file}")

    # Load gzipped JSON
    with gzip.open(segments_file, 'rt', encoding='utf-8') as f:
        all_segments = json.load(f)

    # Take subset
    segments = all_segments[:num_segments]

    logger.info(f"Loaded {len(segments)} segments (out of {len(all_segments)} total)")

    return segments


def test_colab_classifier(segments, character_names, player_names, gdrive_mount_root=None):
    """
    Test the ColabClassifier with the given segments.

    Args:
        segments: List of segment dictionaries with 'text', 'speaker', etc.
        character_names: List of character names
        player_names: List of player names

    Returns:
        List of ClassificationResult objects
    """
    logger.info("Creating ColabClassifier...")

    # Create classifier with auto-detected Google Drive path
    classifier = ClassifierFactory.create(
        backend="colab",
        gdrive_mount_root=gdrive_mount_root,
    )

    logger.info(f"Google Drive pending dir: {classifier.pending_dir}")
    logger.info(f"Google Drive complete dir: {classifier.complete_dir}")

    # Check preflight
    issues = classifier.preflight_check()
    if issues:
        logger.error("Preflight check failed:")
        for issue in issues:
            logger.error(f"  [{issue.severity}] {issue.component}: {issue.message}")
        return None

    logger.info("✓ Preflight check passed")
    logger.info(f"\nStarting classification of {len(segments)} segments...")
    logger.info("=" * 60)
    logger.info("NOTE: Make sure the Colab notebook is running!")
    logger.info("=" * 60)

    # Classify segments
    try:
        results = classifier.classify_segments(
            segments=segments,
            character_names=character_names,
            player_names=player_names
        )

        logger.info(f"\n✓ Classification complete!")
        return results

    except TimeoutError as e:
        logger.error(f"\n❌ {e}")
        logger.error("\nTroubleshooting:")
        logger.error("1. Is the Colab notebook running?")
        logger.error("2. Is Google Drive mounted in Colab?")
        logger.error("3. Check the pending folder in Google Drive")
        return None

    except Exception as e:
        logger.error(f"\n❌ Classification failed: {e}", exc_info=True)
        return None


def print_results(results, segments):
    """Print classification results in a readable format."""
    print("\n" + "=" * 80)
    print("CLASSIFICATION RESULTS")
    print("=" * 80)

    ic_count = sum(1 for r in results if r.classification == "IC")
    ooc_count = sum(1 for r in results if r.classification == "OOC")
    mixed_count = sum(1 for r in results if r.classification == "MIXED")

    print(f"\nSummary:")
    print(f"  IC (In-Character):     {ic_count}")
    print(f"  OOC (Out-of-Character): {ooc_count}")
    print(f"  MIXED:                  {mixed_count}")
    print(f"  Total:                  {len(results)}")

    print("\n" + "-" * 80)
    print("Sample Results (first 10):")
    print("-" * 80)

    for i, (result, segment) in enumerate(list(zip(results, segments))[:10]):
        print(f"\n[{i+1}] {segment['speaker']}: \"{segment['text'][:60]}...\"")
        print(f"    Classification: {result.classification} (confidence: {result.confidence:.2f})")
        if result.character:
            print(f"    Character: {result.character}")
        print(f"    Reasoning: {result.reasoning[:80]}...")


def main():
    parser = argparse.ArgumentParser(description="Test Colab Classifier with checkpoint data")
    parser.add_argument(
        "--checkpoint-dir",
        default="test_s6_nov12_1111am",
        help="Checkpoint directory name (default: test_s6_nov12_1111am)"
    )
    parser.add_argument(
        "--num-segments",
        type=int,
        default=20,
        help="Number of segments to test (default: 20)"
    )
    parser.add_argument(
        "--character-names",
        nargs="+",
        default=["Thorin", "Elara", "Zara"],
        help="Character names (default: Thorin Elara Zara)"
    )
    parser.add_argument(
        "--player-names",
        nargs="+",
        default=["Alice", "Bob", "Charlie", "DM"],
        help="Player names (default: Alice Bob Charlie DM)"
    )
    parser.add_argument(
        "--gdrive-mount",
        default=None,
        help="Google Drive mount root (e.g., 'G:/My Drive')"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("COLAB CLASSIFIER TEST")
    print("=" * 80)
    print(f"\nCheckpoint: {args.checkpoint_dir}")
    print(f"Segments to test: {args.num_segments}")
    print(f"Character names: {', '.join(args.character_names)}")
    print(f"Player names: {', '.join(args.player_names)}")
    print()

    # Load checkpoint data
    try:
        segments = load_checkpoint_segments(args.checkpoint_dir, args.num_segments)
    except Exception as e:
        logger.error(f"Failed to load checkpoint: {e}")
        return 1

    # Test classifier
    results = test_colab_classifier(
        segments=segments,
        character_names=args.character_names,
        player_names=args.player_names,
        gdrive_mount_root=args.gdrive_mount
    )

    if results is None:
        return 1

    # Print results
    print_results(results, segments)

    print("\n" + "=" * 80)
    print("✓ Test completed successfully!")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
