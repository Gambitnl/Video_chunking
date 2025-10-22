# Status Indicators Reference

This reference lists every status indicator exposed by `src/ui/constants.py`. Always import and use the constants rather than hard-coding emoji literals so the UI stays consistent across features and future updates.

## General Status

| Constant | Symbol | Description |
|----------|--------|-------------|
| `SUCCESS` | ✅ | Operation completed successfully |
| `ERROR` | ❌ | Operation failed or unexpected error state |
| `WARNING` | ⚠️ | Needs attention or potential issue |
| `UNKNOWN` | ❓ | Status cannot be determined |

## Health Indicators

| Constant | Symbol | Range | Description |
|----------|--------|-------|-------------|
| `HEALTH_EXCELLENT` | 🟢 | 90-100% | All systems operational |
| `HEALTH_GOOD` | 🟡 | 70-89% | Minor issues present |
| `HEALTH_FAIR` | 🟠 | 50-69% | Significant attention needed |
| `HEALTH_POOR` | 🔴 | 0-49% | Critical issues to address |

## Quest Status

| Constant | Symbol | Description |
|----------|--------|-------------|
| `QUEST_ACTIVE` | 🧭 | Quest in progress |
| `QUEST_COMPLETE` | ✅ | Quest completed successfully |
| `QUEST_FAILED` | ❌ | Quest failed or abandoned |
| `QUEST_UNKNOWN` | ❓ | Quest status unclear |

## Character Development

| Constant | Symbol | Description |
|----------|--------|-------------|
| `PERSONALITY` | 🎭 | Character personality traits |
| `BACKSTORY` | 📜 | Character history and background |
| `FEAR` | 😨 | Character fears and weaknesses |
| `TRAIT` | ✨ | Special abilities or characteristics |
| `DIVINE` | 🛐 | Divine connections or religious aspects |
| `GENERAL` | 🧠 | General character development notes |

## Item Categories

| Constant | Symbol | Description |
|----------|--------|-------------|
| `WEAPON` | 🗡️ | Weapons and offensive items |
| `ARMOR` | 🛡️ | Armor and defensive items |
| `MAGICAL` | 🔮 | Magical items and artifacts |
| `CONSUMABLE` | 🧪 | Potions, scrolls, and one-use items |
| `QUEST_ITEM` | 🏆 | Quest-related items |
| `EQUIPMENT` | 🧰 | Tools and general equipment |
| `MISC` | 🎒 | Miscellaneous items |

## Relationship Types

| Constant | Symbol | Description |
|----------|--------|-------------|
| `ALLY` | 🤝 | Allied characters |
| `ENEMY` | ⚔️ | Hostile characters |
| `NEUTRAL` | 😐 | Neutral relationships |
| `MENTOR` | 🧙 | Teacher or mentor figure |
| `STUDENT` | 🎓 | Student or apprentice |
| `FRIEND` | 🫂 | Close friend or confidant |
| `RIVAL` | 🥊 | Competitive or antagonistic relationship |
| `FAMILY` | 👪 | Family members |
| `DEITY` | 🛐 | Divine beings or gods |
| `SPIRIT` | 👻 | Spiritual or ethereal beings |
| `COMPANION` | 🐾 | Animal companions or familiars |
| `EMPLOYER` | 💼 | Business or professional relationship |
| `MASTER` | 🧑‍🏫 | Authority or instructor figure |
| `RESCUED` | 🆘 | Character rescued or aided |

## Usage Guidelines

1. **Import and use constants**
   ```python
   from src.ui.constants import StatusIndicators

   status = StatusIndicators.SUCCESS  # ✅
   ```
2. **Prefer constants over literals** so downstream changes only need to touch one module.
3. **Contribute new indicators** by updating `src/ui/constants.py` and documenting them here.
