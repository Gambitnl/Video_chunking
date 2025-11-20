# Gradio Theme Toggle (Chronicler-Inspired Skin) Draft
> Drafted: 2025-11-20 | Purpose: Add a toggle-able, darker “Chronicler-inspired” skin to the Modern UI without breaking ASCII/text-only rules.

## Goals
- Provide a selectable skin (classic vs chronicler-inspired) that adjusts colors, spacing, cards, and badges.
- Stay ASCII-only for icons; rely on text badges and lightweight inline SVG if needed.
- Keep changes localized (theme block + small style helpers) to avoid risky rewrites.

## Approach
- Define a Gradio theme variant (extend `gr.themes.Base` or inject CSS) with tokenized colors and spacing.
- Add a UI setting (e.g., “UI skin: classic | chronicler”) stored in session state; default to classic.
- Apply conditional CSS/props across key components (panels, tabs, cards, badges).

## Token Set (example)
- Backgrounds: page `#0b0f18`, panel `#121826`, card `#1a2233`.
- Borders: `#243047`; accents: primary `#6cc3ff`, secondary `#a78bfa`.
- Text: primary `#e5ebf5`, muted `#9fb1c8`; badges neutral `#223045`, success `#1f3b2f`, warn `#3a2e1f`.
- Radius: 10-12px; shadows: subtle `0 8px 24px rgba(0,0,0,0.35)`.

## Implementation Steps (ordered)
1) Create theme module: add `src/ui/theme_presets.py` (or similar) with two presets: `CLASSIC`, `CHRONICLER`. Expose color tokens and a helper to produce a CSS string for Gradio.
2) Wire toggle in UI: in `app.py` settings/tools tab, add a dropdown or radio for “UI skin” persisted in state (default `CLASSIC`). Ensure existing state hydration does not break.
3) Conditional CSS injection: in `app.py` (launch/build UI), inject a `<style>` block or `gr.themes` instance based on selected skin. Scope selectors to our components to avoid Gradio regressions.
4) Component polish: update key panels (knowledge, campaign, process session outputs) to use card wrappers with borders/padding consistent with tokens; replace emoji with text badges per ASCII rule.
5) Badges and chips: add a small helper (e.g., `render_badge(text, tone)`) that maps to CSS classes; reuse across status indicators.
6) Accessibility: verify contrast (WCAG-ish), ensure focus styles visible, and keep font sizes readable.
7) Tests/checks: lightweight smoke to ensure toggle state flips CSS string, and UI still renders with classic skin; manual visual check for both skins.

## Parallelizable Tasks
- Theme token definition and CSS helper (step 1) can proceed in parallel with UI toggle wiring (step 2).
- Component polish (step 4) can be done by feature owners once the token names are fixed.
- Badge helper (step 5) can be implemented independently and then referenced by components.

## Notes
- Keep defaults stable (classic first) to avoid surprising users.
- Avoid pulling Chronicler code; reimplement styles with our tokens.
- If Gradio theming proves brittle, fallback to scoped CSS via `gr.HTML` + a namespace class on the root container.
