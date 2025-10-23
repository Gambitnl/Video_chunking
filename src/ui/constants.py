"""Shared status indicator glyphs for the UI layer."""


class StatusIndicators:
    """Centralised set of status indicator glyphs for the UI."""

    # General status
    SUCCESS = "[OK]"
    ERROR = "[ERROR]"
    WARNING = "[WARN]"
    UNKNOWN = "[UNKNOWN]"

    # Health indicators
    HEALTH_EXCELLENT = "[HEALTH-GREEN]"  # 90-100%
    HEALTH_GOOD = "[HEALTH-YELLOW]"        # 70-89%
    HEALTH_FAIR = "[HEALTH-ORANGE]"        # 50-69%
    HEALTH_POOR = "[HEALTH-RED]"        # 0-49%

    # Quest status
    QUEST_ACTIVE = "[QUEST]"
    QUEST_COMPLETE = SUCCESS
    QUEST_FAILED = ERROR
    QUEST_UNKNOWN = UNKNOWN

    # Character development
    PERSONALITY = "[PERSONALITY]"
    BACKSTORY = "[BACKSTORY]"
    FEAR = "[FEAR]"
    TRAIT = "[TRAIT]"
    DIVINE = "[DIVINE]"
    GENERAL = "[GENERAL]"

    # Item categories
    WEAPON = "[WEAPON]"
    ARMOR = "[ARMOR]"
    MAGICAL = "[MAGIC]"
    CONSUMABLE = "[POTION]"
    QUEST_ITEM = "[QUEST-ITEM]"
    EQUIPMENT = "[GEAR]"
    MISC = "[MISC]"

    # Relationship types
    ALLY = "[ALLY]"
    ENEMY = "[ENEMY]"
    NEUTRAL = "[NEUTRAL]"
    MENTOR = "[MENTOR]"
    STUDENT = "[GRAD]"
    FRIEND = "[FRIEND]"
    RIVAL = "[RIVAL]"
    FAMILY = "[FAMILY]"
    DEITY = "[DEITY]"
    SPIRIT = "[SPIRIT]"
    COMPANION = "[COMPANION]"
    EMPLOYER = "[EMPLOYER]"
    MASTER = "[MASTER]"
    RESCUED = "[RESCUED]"
