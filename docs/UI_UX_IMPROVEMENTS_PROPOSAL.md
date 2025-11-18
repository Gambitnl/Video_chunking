# UI/UX Improvement Proposal: Leveraging Enriched Classification Data

## 1. Executive Summary

The recent backend refactoring has enriched our data model with granular classifications, reliable speaker/character metadata, and scene detection. This document proposes a series of UI/UX improvements designed to leverage this new data, transforming the user experience from a static data review into a dynamic, intuitive, and powerful editing suite for session transcripts.

The core principle is to **empower the user to easily visualize, understand, and correct the AI's output**, creating a virtuous feedback loop that improves the quality of all downstream artifacts (Knowledge Base, Character Profiles, Story Notebooks).

---

## 2. The Transcript Editor: A Dynamic and Interactive Core Experience

The transcript viewer is the central hub of the application. It should be upgraded from a simple text display to a rich, interactive editor.

### Improvement 2.1: Color-Coded Classification
- **What**: Automatically color-code each transcript segment based on its `classification_type`.
- **Why**: This provides an immediate, at-a-glance understanding of the session's flow. The user can instantly distinguish between narration, character dialogue, and OOC chatter without reading a single word.
- **Implementation**:
    - **`DM_NARRATION`**: Render as standard or slightly italicized text. This is the narrative backbone.
    - **`CHARACTER` / `NPC_DIALOGUE`**: Assign a unique, persistent color to each `character_name`. This allows the user to follow a specific character's dialogue throughout the entire transcript effortlessly.
    - **`OOC_OTHER`**: Render in a muted, less prominent color (e.g., grey) to visually de-emphasize it.

### Improvement 2.2: One-Click Classification Override
- **What**: Allow the user to right-click or use a dropdown on any segment to change its `classification_type`.
- **Why**: No AI is perfect. If a critical character action is misclassified as `OOC_OTHER`, the user needs a simple way to correct it. This is the most important feedback loop we can provide.
- **Implementation**: A dropdown menu on each segment showing the four classification types (`CHARACTER`, `DM_NARRATION`, etc.). Selecting a new type flags the segment for reprocessing of downstream artifacts.

### Improvement 2.3: Inline Character Assignment
- **What**: For any segment where `character_name` is "Unknown" or "N/A", display a small warning icon and a dropdown list of all known party characters.
- **Why**: This makes correcting diarization or mapping errors trivial. The user can assign the correct speaker without ever leaving the transcript view.

### Improvement 2.4: Rich Metadata Tooltips
- **What**: On hovering over a segment, display a tooltip showing the rich metadata associated with it.
- **Why**: This provides power users and developers with instant access to debugging information without needing to open the raw JSON.
- **Implementation**: The tooltip should contain:
    - `Classification Confidence`: `98%`
    - `LLM Reasoning`: `"Player is describing a character action."`
    - `Speaker ID`: `SPEAKER_03`
    - `Speaker Name`: `Bob`

---

## 3. Scene-Based Navigation: Mastering the Narrative Flow

The detection of scenes should be a primary navigation tool, allowing users to think in terms of narrative arcs instead of timestamps.

### Improvement 3.1: The Scene Navigator
- **What**: A new UI panel that lists all scenes detected in `stage_6_scenes.json`.
- **Why**: This allows users to jump instantly to relevant parts of the session ("the tavern brawl," "the conversation with the king") instead of scrubbing through a multi-hour timeline.
- **Implementation**:
    - Each item in the list should display the scene's `dominant_type` (e.g., with an icon for "dialogue" or "action"), the characters involved, and the start/end timestamps.
    - Clicking a scene in the navigator instantly scrolls the main transcript editor to the beginning of that scene.

### Improvement 3.2: Scene Manipulation (Advanced)
- **What**: Allow users to select two adjacent scenes and **merge** them, or select a segment and **split** a scene into two at that point.
- **Why**: This gives the user ultimate control over the narrative structure, allowing them to define scene boundaries that match their own understanding of the session's flow.

---

## 4. Integrated Artifact Views: Connecting the Dots

The UI should visually connect the downstream artifacts back to their source in the transcript.

### Improvement 4.1: Linked Knowledge Base
- **What**: When a user views an entity in the Knowledge Base (e.g., an NPC named "Gregor"), they can click a "Find in Transcript" button.
- **Why**: This action should highlight every segment in the transcript that was used to extract or update information about Gregor. This provides perfect traceability and allows the user to verify the source of the information.

### Improvement 4.2: Interactive Story Notebook
- **What**: Display the generated story notebook side-by-side with the transcript.
- **Why**: As the user scrolls through the generated story, the corresponding segments in the transcript that contributed to that paragraph should automatically highlight. This shows the user exactly how the narrative was constructed from the source material.
