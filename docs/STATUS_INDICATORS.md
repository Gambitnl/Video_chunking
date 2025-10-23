# Status Indicators Reference

This reference lists every status indicator exposed by `src/ui/constants.py`. Always import and use the constants rather than hard-coding emoji literals so the UI stays consistent across features and future updates.

## General Status

| Constant | Symbol | Description |
|----------|--------|-------------|
| `SUCCESS` | [OK] | Operation completed successfully |
| `ERROR` | [ERROR] | Operation failed or unexpected error state |
| `WARNING` | [WARN] | Needs attention or potential issue |
| `UNKNOWN` | [UNKNOWN] | Status cannot be determined |

## Health Indicators

| Constant | Symbol | Range | Description |
|----------|--------|-------|-------------|
| `HEALTH_EXCELLENT` | [HEALTH-GREEN] | 90-100% | All systems operational |
| `HEALTH_GOOD` | [HEALTH-YELLOW] | 70-89% | Minor issues present |
| `HEALTH_FAIR` | [HEALTH-ORANGE] | 50-69% | Significant attention needed |
| `HEALTH_POOR` | [HEALTH-RED] | 0-49% | Critical issues to address |

## Quest Status

| Constant | Symbol | Description |
|----------|--------|-------------|
| `QUEST_ACTIVE` | [QUEST] | Quest in progress |
| `QUEST_COMPLETE` | [OK] | Quest completed successfully |
| `QUEST_FAILED` | [ERROR] | Quest failed or abandoned |
| `QUEST_UNKNOWN` | [UNKNOWN] | Quest status unclear |

## Character Development

| Constant | Symbol | Description |
|----------|--------|-------------|
| `PERSONALITY` | [PERSONALITY] | Character personality traits |
| `BACKSTORY` | [BACKSTORY] | Character history and background |
| `FEAR` | [FEAR] | Character fears and weaknesses |
| `TRAIT` | [TRAIT] | Special abilities or characteristics |
| `DIVINE` | [DIVINE] | Divine connections or religious aspects |
| `GENERAL` | [GENERAL] | General character development notes |

## Item Categories

| Constant | Symbol | Description |
|----------|--------|-------------|
| `WEAPON` | [WEAPON] | Weapons and offensive items |
| `ARMOR` | [ARMOR] | Armor and defensive items |
| `MAGICAL` | [MAGIC] | Magical items and artifacts |
| `CONSUMABLE` | [POTION] | Potions, scrolls, and one-use items |
| `QUEST_ITEM` | [QUEST-ITEM] | Quest-related items |
| `EQUIPMENT` | [GEAR] | Tools and general equipment |
| `MISC` | [MISC] | Miscellaneous items |

## Relationship Types

| Constant | Symbol | Description |
|----------|--------|-------------|
| `ALLY` | [ALLY] | Allied characters |
| `ENEMY` | [ENEMY] | Hostile characters |
| `NEUTRAL` | [NEUTRAL] | Neutral relationships |
| `MENTOR` | [MENTOR] | Teacher or mentor figure |
| `STUDENT` | [GRAD] | Student or apprentice |
| `FRIEND` | [FRIEND] | Close friend or confidant |
| `RIVAL` | [RIVAL] | Competitive or antagonistic relationship |
| `FAMILY` | [FAMILY] | Family members |
| `DEITY` | [DEITY] | Divine beings or gods |
| `SPIRIT` | [SPIRIT] | Spiritual or ethereal beings |
| `COMPANION` | [COMPANION] | Animal companions or familiars |
| `EMPLOYER` | [EMPLOYER] | Business or professional relationship |
| `MASTER` | [MASTER] | Authority or instructor figure |
| `RESCUED` | [RESCUED] | Character rescued or aided |

## Usage Guidelines

1. **Import and use constants**
   ```python
   from src.ui.constants import StatusIndicators

   status = StatusIndicators.SUCCESS  # [OK]
   ```
2. **Prefer constants over literals** so downstream changes only need to touch one module.
3. **Contribute new indicators** by updating `src/ui/constants.py` and documenting them here.
