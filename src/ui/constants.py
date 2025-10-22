"""Shared status indicator glyphs for the UI layer."""


class StatusIndicators:
    """Centralised set of status indicator glyphs for the UI."""

    # General status
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    UNKNOWN = "❓"

    # Health indicators
    HEALTH_EXCELLENT = "🟢"  # 90-100%
    HEALTH_GOOD = "🟡"        # 70-89%
    HEALTH_FAIR = "🟠"        # 50-69%
    HEALTH_POOR = "🔴"        # 0-49%

    # Quest status
    QUEST_ACTIVE = "🧭"
    QUEST_COMPLETE = SUCCESS
    QUEST_FAILED = ERROR
    QUEST_UNKNOWN = UNKNOWN

    # Character development
    PERSONALITY = "🎭"
    BACKSTORY = "📜"
    FEAR = "😨"
    TRAIT = "✨"
    DIVINE = "🛐"
    GENERAL = "🧠"

    # Item categories
    WEAPON = "🗡️"
    ARMOR = "🛡️"
    MAGICAL = "🔮"
    CONSUMABLE = "🧪"
    QUEST_ITEM = "🏆"
    EQUIPMENT = "🧰"
    MISC = "🎒"

    # Relationship types
    ALLY = "🤝"
    ENEMY = "⚔️"
    NEUTRAL = "😐"
    MENTOR = "🧙"
    STUDENT = "🎓"
    FRIEND = "🫂"
    RIVAL = "🥊"
    FAMILY = "👪"
    DEITY = "🛐"
    SPIRIT = "👻"
    COMPANION = "🐾"
    EMPLOYER = "💼"
    MASTER = "🧑‍🏫"
    RESCUED = "🆘"
