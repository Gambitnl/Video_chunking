"""
Unit tests for character analytics module.

Tests the CharacterAnalytics class including timeline generation,
action filtering, and progression statistics.
"""
import pytest
from pathlib import Path
from typing import List

from src.character_profile import (
    CharacterProfile,
    CharacterProfileManager,
    CharacterAction,
    CharacterItem,
    CharacterRelationship,
    CharacterDevelopment,
    CharacterQuote,
)
from src.analytics.character_analytics import (
    CharacterAnalytics,
    TimelineEvent,
    CharacterTimeline,
)


@pytest.fixture
def temp_profile_dir(tmp_path):
    """Create temporary directory for test profiles."""
    profile_dir = tmp_path / "test_profiles"
    profile_dir.mkdir()
    return profile_dir


@pytest.fixture
def profile_manager(temp_profile_dir):
    """Create character profile manager with test data."""
    manager = CharacterProfileManager(profiles_dir=temp_profile_dir)

    # Create test character with comprehensive data
    profile = CharacterProfile(
        name="Thorin",
        player="Alice",
        race="Dwarf",
        class_name="Fighter",
        level=5,
        description="A sturdy dwarf warrior",
        campaign_id="test_campaign",
        campaign_name="Test Campaign",
        sessions_appeared=["session_001", "session_002", "session_003"],
        total_sessions=3,
        notable_actions=[
            CharacterAction(
                session="session_001",
                timestamp="00:15:30",
                description="Attacked goblin with warhammer",
                type="combat"
            ),
            CharacterAction(
                session="session_001",
                timestamp="00:45:00",
                description="Persuaded merchant for better price",
                type="social"
            ),
            CharacterAction(
                session="session_002",
                timestamp="01:10:00",
                description="Explored dark cavern",
                type="exploration"
            ),
            CharacterAction(
                session="session_003",
                description="Cast protective spell",
                type="magic"
            ),
        ],
        memorable_quotes=[
            CharacterQuote(
                session="session_001",
                quote="By Moradin's beard!",
                context="Battle cry"
            ),
            CharacterQuote(
                session="session_002",
                quote="We must press on",
                context="Encouraging party"
            ),
        ],
        development_notes=[
            CharacterDevelopment(
                session="session_001",
                note="Overcame fear of heights",
                category="personality"
            ),
        ],
        inventory=[
            CharacterItem(
                name="+1 Warhammer",
                description="Magical warhammer",
                session_acquired="session_001",
                category="weapon"
            ),
            CharacterItem(
                name="Healing Potion",
                description="Restores 2d4+2 HP",
                session_acquired="session_002",
                category="consumable"
            ),
        ],
        relationships=[
            CharacterRelationship(
                name="Elara",
                relationship_type="ally",
                description="Fellow adventurer",
                first_met="session_001"
            ),
            CharacterRelationship(
                name="Shadow Lord",
                relationship_type="enemy",
                description="Main antagonist",
                first_met="session_002"
            ),
        ],
    )

    manager.add_profile("Thorin", profile)
    return manager


@pytest.fixture
def analytics(profile_manager):
    """Create analytics engine with test data."""
    return CharacterAnalytics(profile_manager)


# ========== Timeline Generation Tests ==========

def test_generate_timeline_basic(analytics):
    """Test basic timeline generation."""
    timeline = analytics.generate_timeline("Thorin")

    assert isinstance(timeline, CharacterTimeline)
    assert timeline.character_name == "Thorin"
    assert len(timeline.events) > 0
    assert len(timeline.sessions) == 3
    assert timeline.total_events == len(timeline.events)


def test_generate_timeline_includes_all_event_types(analytics):
    """Test that timeline includes all event types."""
    timeline = analytics.generate_timeline("Thorin")

    event_types = {event.event_type for event in timeline.events}
    assert "action" in event_types
    assert "quote" in event_types
    assert "development" in event_types
    assert "item" in event_types
    assert "relationship" in event_types


def test_generate_timeline_session_filter(analytics):
    """Test timeline generation with session filter."""
    timeline = analytics.generate_timeline("Thorin", session_filter=["session_001"])

    assert len(timeline.sessions) == 1
    assert timeline.sessions[0] == "session_001"

    # All events should be from session_001
    for event in timeline.events:
        assert event.session_id == "session_001"


def test_generate_timeline_event_type_filter(analytics):
    """Test timeline generation with event type filter."""
    timeline = analytics.generate_timeline("Thorin", event_types=["action"])

    # Should only have action events
    for event in timeline.events:
        assert event.event_type == "action"


def test_generate_timeline_chronological_order(analytics):
    """Test that timeline events are in chronological order."""
    timeline = analytics.generate_timeline("Thorin")

    # Events should be sorted by session and then by timestamp
    # Check that session order matches sessions_appeared
    session_indices = {}
    for event in timeline.events:
        if event.session_id not in session_indices:
            session_indices[event.session_id] = len(session_indices)

    # Session indices should be in order (0, 1, 2, ...)
    assert list(session_indices.values()) == sorted(session_indices.values())


def test_generate_timeline_invalid_character(analytics):
    """Test timeline generation for non-existent character."""
    with pytest.raises(ValueError, match="not found"):
        analytics.generate_timeline("NonExistent")


# ========== Action Filtering Tests ==========

def test_filter_actions_by_type(analytics):
    """Test filtering actions by type."""
    actions = analytics.filter_actions("Thorin", action_types=["combat"])

    assert len(actions) == 1
    assert actions[0].type == "combat"
    assert "warhammer" in actions[0].description.lower()


def test_filter_actions_by_session(analytics):
    """Test filtering actions by session."""
    actions = analytics.filter_actions("Thorin", sessions=["session_001"])

    assert len(actions) == 2  # 2 actions in session_001
    for action in actions:
        assert action.session == "session_001"


def test_filter_actions_by_text_search(analytics):
    """Test filtering actions by text search."""
    actions = analytics.filter_actions("Thorin", text_search="goblin")

    assert len(actions) == 1
    assert "goblin" in actions[0].description.lower()


def test_filter_actions_multiple_criteria(analytics):
    """Test filtering with multiple criteria."""
    actions = analytics.filter_actions(
        "Thorin",
        action_types=["combat", "social"],
        sessions=["session_001"]
    )

    assert len(actions) == 2
    for action in actions:
        assert action.type in ["combat", "social"]
        assert action.session == "session_001"


def test_filter_actions_no_matches(analytics):
    """Test filtering that returns no matches."""
    actions = analytics.filter_actions("Thorin", text_search="nonexistent")

    assert len(actions) == 0


def test_filter_actions_invalid_character(analytics):
    """Test filtering for non-existent character."""
    with pytest.raises(ValueError, match="not found"):
        analytics.filter_actions("NonExistent")


# ========== Progression Statistics Tests ==========

def test_get_progression_stats_basic(analytics):
    """Test basic progression statistics."""
    stats = analytics.get_progression_stats("Thorin")

    assert stats["character_name"] == "Thorin"
    assert stats["level"] == 5
    assert stats["total_sessions"] == 3
    assert stats["total_actions"] == 4
    assert stats["total_items"] == 2
    assert stats["total_relationships"] == 2
    assert stats["total_quotes"] == 2
    assert stats["total_developments"] == 1


def test_get_progression_stats_actions_by_type(analytics):
    """Test action counts by type."""
    stats = analytics.get_progression_stats("Thorin")

    actions_by_type = stats["actions_by_type"]
    assert actions_by_type["combat"] == 1
    assert actions_by_type["social"] == 1
    assert actions_by_type["exploration"] == 1
    assert actions_by_type["magic"] == 1


def test_get_progression_stats_session_progression(analytics):
    """Test session-by-session progression data."""
    stats = analytics.get_progression_stats("Thorin")

    progression = stats["session_progression"]
    assert len(progression) == 3

    # Check session_001 stats
    session_001_stats = next(s for s in progression if s["session_id"] == "session_001")
    assert session_001_stats["actions"] == 2
    assert session_001_stats["items_acquired"] == 1
    assert session_001_stats["relationships_formed"] == 1


def test_get_progression_stats_invalid_character(analytics):
    """Test stats for non-existent character."""
    with pytest.raises(ValueError, match="not found"):
        analytics.get_progression_stats("NonExistent")


# ========== Activity Summary Tests ==========

def test_get_character_activity_summary(analytics):
    """Test generating activity summary."""
    summary = analytics.get_character_activity_summary("Thorin")

    assert isinstance(summary, str)
    assert "Thorin" in summary
    assert "Level" in summary
    assert "Sessions" in summary
    assert "Action Distribution" in summary
    assert "combat" in summary.lower()


# ========== TimelineEvent Tests ==========

def test_timeline_event_creation():
    """Test creating timeline events."""
    event = TimelineEvent(
        session_id="session_001",
        timestamp="00:15:30",
        event_type="action",
        description="Test action",
        category="combat"
    )

    assert event.session_id == "session_001"
    assert event.timestamp == "00:15:30"
    assert event.event_type == "action"
    assert event.description == "Test action"
    assert event.category == "combat"


def test_timeline_event_invalid_type():
    """Test creating event with invalid type."""
    with pytest.raises(ValueError, match="Invalid event_type"):
        TimelineEvent(
            session_id="session_001",
            event_type="invalid_type",
            description="Test"
        )


def test_timeline_event_with_metadata():
    """Test creating event with metadata."""
    event = TimelineEvent(
        session_id="session_001",
        event_type="item",
        description="Found sword",
        metadata={"item_name": "Sword", "rarity": "common"}
    )

    assert event.metadata["item_name"] == "Sword"
    assert event.metadata["rarity"] == "common"


# ========== Timestamp Parsing Tests ==========

def test_parse_timestamp_to_seconds_mmss(analytics):
    """Test parsing MM:SS timestamp."""
    seconds = analytics._parse_timestamp_to_seconds("15:30")
    assert seconds == 15 * 60 + 30


def test_parse_timestamp_to_seconds_hhmmss(analytics):
    """Test parsing HH:MM:SS timestamp."""
    seconds = analytics._parse_timestamp_to_seconds("01:15:30")
    assert seconds == 1 * 3600 + 15 * 60 + 30


def test_parse_timestamp_to_seconds_none(analytics):
    """Test parsing None timestamp."""
    seconds = analytics._parse_timestamp_to_seconds(None)
    assert seconds == 999999.0  # Default for missing timestamps


def test_parse_timestamp_to_seconds_invalid(analytics):
    """Test parsing invalid timestamp."""
    seconds = analytics._parse_timestamp_to_seconds("invalid")
    assert seconds == 999999.0


# ========== Edge Cases Tests ==========

def test_timeline_empty_profile(temp_profile_dir):
    """Test timeline for character with no data."""
    manager = CharacterProfileManager(profiles_dir=temp_profile_dir)
    profile = CharacterProfile(
        name="Empty",
        player="Test",
        race="Human",
        class_name="Wizard",
        level=1
    )
    manager.add_profile("Empty", profile)

    analytics = CharacterAnalytics(manager)
    timeline = analytics.generate_timeline("Empty")

    assert timeline.total_events == 0
    assert len(timeline.events) == 0
    assert len(timeline.sessions) == 0


def test_filter_actions_empty_profile(temp_profile_dir):
    """Test filtering actions for character with no actions."""
    manager = CharacterProfileManager(profiles_dir=temp_profile_dir)
    profile = CharacterProfile(
        name="Empty",
        player="Test",
        race="Human",
        class_name="Wizard",
        level=1
    )
    manager.add_profile("Empty", profile)

    analytics = CharacterAnalytics(manager)
    actions = analytics.filter_actions("Empty")

    assert len(actions) == 0
