# Knowledge Board Reimplementation Outline (No Code Copy)
> Drafted: 2025-11-20 | Source inspiration: ffmpeg_shared/Chronicler-ai (UI only, no code reuse)

## Goals
- Recreate a vibrant knowledge board for sessions: character profile cards + world entities grid.
- Use our pipeline outputs (knowledge base, profiles) and adhere to ASCII-only UI text/icons policy.
- Integrate with Modern UI (Gradio) without importing external React code.

## Data Mapping
- Entities: name, type (location/npc/quest/item/faction/other), description, status (optional), id.
- Profiles: name, class/role, status, inventory (list), active goals/quests (list), notes/banter.
- Source: existing knowledge extraction outputs (check `knowledge_base.json` or equivalent stage artifacts).

## Layout (to implement natively)
- Section 1: Character Profiles (Updated)
  - Card per profile: header with name + class, status badge, inventory chips, active goals list, short notes block.
- Section 2: Extracted World Knowledge
  - Grid of cards: type badge, name, short description (line-clamped), optional status pill (e.g., “active”, “rumor”).
- Styling: dark cards with subtle borders; replace icons with ASCII labels and our StatusIndicators where needed.

## Interactions
- Filters: by type (locations, quests, NPCs, items, factions), by status, by search text.
- Sorting: recency (if timestamps available) or alphabetic.
- Empty states: clear message and CTA to run analysis.
- Optional: click-through to open full description/links in a modal/panel.

## Integration Points
- Read from session artifacts (current session selection) cached in UI; avoid reprocessing.
- Respect existing campaign/session filters in Modern UI.
- Ensure outputs remain under `output/<session>/...` and do not alter pipeline generation paths.

## Implementation Steps (ordered)
1) Define lightweight data adapters to load knowledge entities and profiles from existing artifacts (Python-side helper).
2) Add UI components in our stack (e.g., `src/ui/knowledge_board.py` or within modern tab) rendering the two sections.
3) Implement filters/sorting (type/status/search) and empty states.
4) Add optional detail modal/panel for long descriptions.
5) Wire into Modern UI navigation (new tab or existing knowledge section).
6) Add smoke tests for the data adapter and UI rendering with sample fixtures.

## Parallelizable Tasks
- Data adapter + fixtures can proceed while UI layout is built, once the target schema is agreed.
- Filters/sorting logic can be developed independently of styling.
- Tests (fixtures + smoke) can be prepared in parallel with UI wiring.

## Non-Copy Commitment
- Do not import or reuse Chronicler React/Vite code; reimplement layout semantics in our UI framework using our styling and ASCII-only rules.
