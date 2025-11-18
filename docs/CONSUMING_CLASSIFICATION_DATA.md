# Guide: Consuming Enriched Classification Data

This document outlines the structure of the data produced by the classification pipeline (Stage 6) and provides best practices for building downstream tools that consume this information. As of the latest update, the classification output is significantly richer, containing granular types and reliable metadata that should be used in place of older, text-parsing methods.

## Data Artifacts

The classification stage now produces up to two key files in the `intermediates` directory of a session's output:

1.  `stage_6_classification.json`: A JSON array where each object represents a single classified segment. **This is the primary source of truth.**
2.  `stage_6_scenes.json`: (Optional) A JSON array that groups the segments from the file above into narrative scenes. This is useful for context-aware processing.

---

## The `ClassificationResult` Object Shape

Each object in `stage_6_classification.json` follows the `ClassificationResult` shape. Downstream consumers should rely on these fields.

### Key Fields:

| Field                 | Type   | Description                                                                                                                                 |
| --------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `text`                | string | The transcribed text of the segment.                                                                                                        |
| `start_time`          | float  | Start time of the segment in seconds.                                                                                                       |
| `end_time`            | float  | End time of the segment in seconds.                                                                                                         |
| `speaker`             | string | The raw speaker ID from diarization (e.g., `SPEAKER_00`).                                                                                   |
| `speaker_name`        | string | **(New & Reliable)** The mapped name of the speaker (player), e.g., "Alice".                                                                |
| `character_name`      | string | **(New & Reliable)** The mapped name of the character being portrayed, e.g., "Sha'ek Mindfa'ek". Can also be "DM" or "Unknown".             |
| `classification`      | string | The primary classification, for backward compatibility. Either `IC` (In-Character) or `OOC` (Out-of-Character).                             |
| `classification_type` | string | **(New & Authoritative)** The granular classification type. This should be preferred over the `classification` field for all new development. |
| `confidence`          | float  | The confidence score of the classification (0.0 to 1.0).                                                                                    |
| `reasoning`           | string | The LLM's reasoning for its classification. Useful for debugging.                                                                           |

### Granular Classification Types (`classification_type`)

This is the most important new field for building accurate downstream tools.

| Type             | Description                                                                                                                                                           |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CHARACTER`      | A player speaking as their character or declaring a narrative-relevant action. **This is the primary type for character-centric tools.**                                |
| `DM_NARRATION`   | The Dungeon Master describing a scene, action, or outcome. This is the narrative prose of the story.                                                                  |
| `NPC_DIALOGUE`   | The Dungeon Master speaking as a Non-Player Character (NPC).                                                                                                          |
| `OOC_OTHER`      | Any out-of-character speech, including rule discussions, meta-gaming, or table talk. This content is generally not relevant for narrative or story generation.         |

---

## The `Scene` Object Shape

The optional `stage_6_scenes.json` file is an array of scene objects. A scene is a continuous block of narratively relevant segments.

| Field           | Type          | Description                                                              |
| --------------- | ------------- | ------------------------------------------------------------------------ |
| `scene_index`   | integer       | The sequential index of the scene.                                       |
| `start_time`    | float         | The start time of the first segment in the scene.                        |
| `end_time`      | float         | The end time of the last segment in the scene.                           |
| `dominant_type` | string        | The most frequent `classification_type` within the scene.                |
| `speaker_list`  | List[string]  | A unique list of `character_name` values for all speakers in the scene.  |
| `segment_ids`   | List[integer] | A list of `segment_index` values for all segments included in this scene. |

---

## Best Practices for Consumers

### 1. Filter by `classification_type`
Do not rely on the old `classification == "IC"` check. Instead, filter for the specific types relevant to your tool. For most narrative purposes, you should process a list of types.

```python
# Good: Process all narratively relevant segments
NARRATIVE_TYPES = {"CHARACTER", "DM_NARRATION", "NPC_DIALOGUE"}
narrative_segments = [
    s for s in all_segments if s.get("classification_type") in NARRATIVE_TYPES
]

# Good: Process only segments spoken by a player character
character_segments = [
    s for s in all_segments if s.get("classification_type") == "CHARACTER"
]
```

### 2. Use Reliable Metadata
Always use the `character_name` and `speaker_name` fields. **Do not** attempt to parse character or speaker names from the `text` field. The new metadata is the source of truth.

```python
# Good
actor = segment.get("character_name") or "Unknown"
print(f'{actor}: "{segment["text"]}"')

# Bad (Old Method)
# actor, text = segment["text"].split(":", 1)
```

### 3. Build Story-Like Transcripts
When feeding data to another LLM (e.g., for summarization), format the input as a story, not a raw transcript. This produces significantly better results.

**Example Implementation:**
```python
story_parts = []
for segment in narrative_segments:
    text = segment.get("text", "").strip()
    if not text:
        continue
    
    # Narration is prose
    if segment["classification_type"] == "DM_NARRATION":
        story_parts.append(text)
    
    # Dialogue is quoted and attributed
    elif segment["classification_type"] in ("CHARACTER", "NPC_DIALOGUE"):
        actor = segment.get("character_name", "Unknown")
        story_parts.append(f'{actor}: "{text}"')

final_transcript = "\n\n".join(story_parts)
```

### 4. Use Scenes for Context
If your tool benefits from processing the story in larger chunks (e.g., summarizing one scene at a time), use `stage_6_scenes.json`. You can use the `segment_ids` in each scene object to look up the full segment data from `stage_6_classification.json`. This is more robust than implementing your own scene-break logic.

### 5. Leverage Scene-Aware Processing
For the highest quality results, especially when making calls to an LLM, consumers should adopt a scene-aware processing architecture. Instead of processing all segments from a session at once, use the `stage_6_scenes.json` file to process the session scene by scene.

**Benefits:**
- **Improved Contextual Accuracy**: An LLM has a much better chance of extracting relevant information (e.g., a specific quest detail or a notable character action) when it only sees the small, focused transcript of a single scene.
- **Higher Quality Output**: This prevents information from unrelated parts of the session from confusing the LLM.
- **Better Performance**: Processing smaller chunks can lead to faster and more reliable LLM calls.

**Example Architecture (`KnowledgeExtractor`):**
1. Load all segments from `stage_6_classification.json` into a dictionary for quick lookups.
2. Load the list of scenes from `stage_6_scenes.json`.
3. Loop through each scene object.
4. For each scene, gather the corresponding segments from the dictionary.
5. Call the LLM with this small, contextually relevant batch of segments.
6. After processing all scenes, perform a final "deep merge" of the results to create a complete, enriched collection of data.

This pattern is more complex than single-pass processing but produces significantly more accurate and relevant results. It is the recommended approach for all new extraction tools.

---

## Handling Legacy Data

The refactored downstream consumers (`KnowledgeExtractor`, `CharacterProfileExtractor`, etc.) have been designed with backward compatibility in mind.

If a segment is missing the new `classification_type` field (which will be the case for session data processed before this change), the tools will automatically fall back to using the older `classification` field.

**Fallback Logic:**
```python
is_narrative = False
if "classification_type" in segment:
    is_narrative = segment["classification_type"] in NARRATIVE_TYPES
elif segment.get("classification") == "IC":
    # Fallback for older data formats
    is_narrative = True
```

This ensures that older data can still be processed without errors. However, for best results and maximum accuracy, it is recommended to re-process older sessions through the new classification pipeline to generate the enriched metadata.

