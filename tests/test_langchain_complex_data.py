"""
Tests for BUG-20251102-34: Improve test data complexity.
Uses rich, nested, and realistic D&D data to verify system robustness.
"""
import pytest
from pathlib import Path
import json
from unittest.mock import MagicMock, Mock

from src.langchain.retriever import CampaignRetriever

@pytest.fixture
def complex_data_dirs(tmp_path):
    kb_dir = tmp_path / "knowledge"
    transcript_dir = tmp_path / "transcripts"
    vector_dir = tmp_path / "vector_db"

    kb_dir.mkdir()
    transcript_dir.mkdir()
    vector_dir.mkdir()

    return kb_dir, transcript_dir, vector_dir

def test_complex_knowledge_structure_ingestion(complex_data_dirs):
    """Test ingestion and retrieval of deeply nested and complex JSON structures."""
    kb_dir, transcript_dir, vector_dir = complex_data_dirs

    # Complex nested data simulating a real campaign entity
    complex_entity = {
        "name": "The Obsidian Citadel",
        "type": "location",
        "description": "A fortress made of black glass.",
        "details": {
            "history": {
                "founded": "Age of Ash",
                "founder": "Sorcerer King",
                "events": [
                    {"year": -500, "event": "Construction began"},
                    {"year": -450, "event": "First siege"}
                ]
            },
            "inhabitants": [
                {"race": "Fire Giants", "population": 50, "leader": "Ignis"},
                {"race": "Salamanders", "population": 200}
            ],
            "magical_properties": {
                "aura": "Desecration",
                "effects": ["Fire resistance", "Fear aura"]
            }
        },
        "relationships": {
            "allies": ["Red Dragon Flight"],
            "enemies": ["Kingdom of Valoria", "Order of the White Shield"]
        }
    }

    # Save to file
    (kb_dir / "complex_location_knowledge.json").write_text(json.dumps({"locations": [complex_entity]}), encoding="utf-8")

    # Initialize Retriever
    retriever = CampaignRetriever(kb_dir, transcript_dir)

    # Retrieve by deep nested field
    results = retriever.retrieve("Ignis", top_k=5)

    assert len(results) > 0
    # Verify the whole document is returned/accessible
    assert "Obsidian Citadel" in results[0].page_content
    assert "Fire Giants" in results[0].page_content

def test_complex_transcript_dialogue(complex_data_dirs):
    """Test retrieval from transcript with complex dialogue patterns."""
    kb_dir, transcript_dir, vector_dir = complex_data_dirs

    session_dir = transcript_dir / "session_complex"
    session_dir.mkdir()

    segments = [
        {
            "text": "Elara (whispering): Do you hear that? It sounds like... <clanking chains>.",
            "speaker": "Elara",
            "start": 10.0, "end": 15.0
        },
        {
            "text": "DM: The chains rattle louder. *Clank. Clank.* A voice booms: \"WHO DISTURBS MY SLUMBER?\"",
            "speaker": "DM",
            "start": 15.0, "end": 20.0
        },
        {
            "text": "Thorin: I draw my hammer! \"Show yourself, coward!\"",
            "speaker": "Thorin",
            "start": 20.0, "end": 25.0
        }
    ]

    (session_dir / "diarized_transcript.json").write_text(json.dumps({"segments": segments}), encoding="utf-8")

    retriever = CampaignRetriever(kb_dir, transcript_dir)

    # Search for sound effect
    results = retriever.retrieve("clanking chains", top_k=5)
    assert len(results) > 0
    assert "Elara" in results[0].metadata["speaker"]

    # Search for quoted dialogue
    results = retriever.retrieve("Show yourself", top_k=5)
    assert len(results) > 0
    assert "Thorin" in results[0].metadata["speaker"]
