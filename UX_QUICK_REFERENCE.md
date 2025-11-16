# UX Landscape - Quick Reference Guide

## 📱 Application at a Glance

| Aspect | Details |
|--------|---------|
| **Type** | Gradio web application (Python backend) |
| **Purpose** | Process D&D session recordings → transcripts + speaker ID + content classification |
| **Framework** | Gradio + Python |
| **Entry Point** | `http://127.0.0.1:7860` |
| **Main File** | `/app.py` (1,699 lines) |
| **UI Modules** | 33 files in `/src/ui/` (297 KB) |
| **Color Scheme** | Indigo/Cyan modern palette |
| **Recent Update** | UI modernized: 16 tabs → 5 main sections (Oct 2025) |

---

## 🎯 Main User Interfaces

### Landing Page: Campaign Launcher
- Load existing campaign or create new one
- Campaign manifest shows stats
- Two-column layout (Load | Create)

### 5 Main Tabs:

| Tab | Purpose | Key Components |
|-----|---------|-----------------|
| **Process Session** | Upload & process recordings | 4-step workflow (Upload→Configure→Process→Review) |
| **Campaign** | Manage campaign data | Overview, Knowledge Base, Session Library |
| **Characters** | Track character development | Character table, profiles, export/import |
| **Stories & Output** | Browse results | Transcripts, search, narratives |
| **Settings & Tools** | Configure & analyze | API keys, models, diagnostics, chat, insights |

---

## 🎨 Design System

### Color Palette
- **Primary**: Indigo `#6366f1` (hover: `#4f46e5`)
- **Accent**: Cyan `#06b6d4`
- **Status**: Green (success), Amber (warning), Red (error), Blue (info)

### Component Patterns
- **Buttons**: 3 variants (primary/secondary/stop), 3 sizes (sm/md/lg)
- **Status Messages**: Icon + header + message + optional details
- **Forms**: Textbox, Slider, Dropdown, Checkbox, File upload
- **Containers**: Groups, Rows, Columns, Accordions (collapsible)

### Progressive Disclosure
- Basic options visible by default
- Advanced options in collapsible accordions
- 10+ accordion sections in Settings tab

---

## 🔧 UI Code Patterns (Strengths)

✅ **Builder Pattern**: Modular component creation
✅ **Event Wiring**: Separated from UI structure
✅ **Status Messages**: Reusable formatting system
✅ **Campaign Context**: Shared state across tabs
✅ **Input Validation**: Safe type casting, format hints
✅ **Configuration as Code**: `.env` based settings

---

## ⚠️ Key UX Issues

### Critical (High Impact)
1. **No real-time form validation** - Invalid inputs accepted silently
2. **Text-only progress** - Long tasks show no visual progress bar
3. **File history warning** - Doesn't prevent duplicate processing
4. **No campaign breadcrumb** - Users may lose context across tabs

### Usability (Medium Impact)
5. **Crowded Settings tab** - 10+ accordions overwhelming
6. **Empty states** - No clear call-to-action for new users
7. **Session library** - Markdown list not interactive
8. **Results display** - Plain text, hard to copy/format

### Accessibility (Important)
9. **No keyboard shortcuts** - Power users disadvantaged
10. **No ARIA labels** - Screen reader support unclear
11. **No mobile design** - Small screen layouts broken
12. **Color contrast** - Not verified against WCAG AA

### Performance
13. **5-minute cache** - Campaign artifacts lag behind reality
14. **Large tables** - 100+ rows may slow down
15. **Orphaned files** - Reprocessing leaves stray audio

---

## 🚀 Recommended Improvements

### High Priority (Quick Wins)
- [ ] Add onChange validators to Session ID input
- [ ] Replace text progress with CSS progress bars
- [ ] Add campaign context badge in header
- [ ] Enhance empty state messages with buttons
- [ ] Add Ctrl+Enter keyboard shortcut to process

### Medium Priority (1-2 sprints)
- [ ] Reorganize Settings by domain (AI, Processing, Advanced)
- [ ] Convert session library to interactive dataframe
- [ ] Accessibility audit (WCAG AA compliance)
- [ ] Mobile responsive design (mobile-first)
- [ ] Transcript syntax highlighting + copy buttons

### Lower Priority (Polish)
- [ ] Tooltip system for complex options
- [ ] Drag-and-drop file upload
- [ ] Accordion state persistence
- [ ] Session template system
- [ ] Undo/redo for forms

---

## 📁 Key Files by Purpose

### Design & Styling
- `src/ui/theme.py` - Color palette, CSS
- `src/ui/constants.py` - Status indicator glyphs
- `src/ui/helpers.py` - StatusMessages, UIComponents classes

### Process Session (Main Workflow)
- `src/ui/process_session_tab_modern.py` - Orchestrator
- `src/ui/process_session_components.py` - Builder classes
- `src/ui/process_session_events.py` - Event handlers
- `src/ui/process_session_helpers.py` - Validation logic

### Other Tabs
- `src/ui/campaign_tab_modern.py` - Campaign overview
- `src/ui/characters_tab_modern.py` - Character management
- `src/ui/stories_output_tab_modern.py` - Transcripts
- `src/ui/settings_tools_tab_modern.py` - Settings umbrella

### Feature Areas
- `src/ui/social_insights_tab.py` - Banter analysis
- `src/ui/speaker_manager_tab.py` - Speaker mapping
- `src/ui/campaign_chat_tab.py` - LLM chat
- `src/ui/campaign_dashboard_tab.py` - Health check

---

## 🧪 Component Inventory

### Form Inputs
- Textbox (plain text, password, multi-line)
- Slider (numeric with min/max/step)
- Dropdown (single/multiple select)
- Checkbox (toggle)
- File upload (with type filtering)
- Number (with safe casting)

### Display Components
- Markdown (rich text, status messages)
- Textbox (read-only, for logs)
- Dataframe (sortable table)
- HTML (custom markup)
- Image (placeholder for word clouds)

### Containers
- Group (card-like section)
- Row (horizontal layout)
- Column (vertical layout)
- Accordion (collapsible section)
- Tab (tab panel)

### Controls
- Button (primary/secondary/stop variants)
- Timer (auto-refresh polling)
- State (campaign context)

---

## 📊 Application Flow

```
User Opens App
    ↓
Campaign Launcher
    ├→ Load Campaign (loads defaults)
    └→ Create New Campaign (blank slate)
    ↓
Select Workflow Tab
    ├→ Process Session (main workflow)
    ├→ Campaign (view data)
    ├→ Characters (manage profiles)
    ├→ Stories (browse results)
    └→ Settings (configure)
    ↓
Complete Tab Actions
    ↓
Results Display + Campaign Updates
```

---

## 🎓 For UX Improvements

### Entry Points
1. **Form Validation**: `/src/ui/process_session_helpers.py` - Add real-time validators
2. **Progress Display**: `/src/ui/process_session_components.py` - Replace markdown with visual bars
3. **Settings Organization**: `/src/ui/settings_tools_tab_modern.py` - Refactor accordions
4. **Accessibility**: `/src/ui/theme.py` - Add ARIA labels + keyboard support
5. **Mobile Design**: `/src/ui/theme.py` - Add responsive CSS

### Best Practices Already in Place
- Use StatusMessages helper for consistent formatting
- Use UIComponents.create_action_button() for buttons
- Follow builder pattern for new sections
- Keep event wiring separate from UI structure
- Use component references dictionary for flexibility

---

## 📝 Development Notes

**Testing**: 100+ test files in `/tests/` (pytest-based)
**Documentation**: See `/IMPLEMENTATION_PLANS_SUMMARY.md` for feature roadmap
**Configuration**: Loads from `.env` file with environment variables
**Logging**: Uses `src/logger.py` with configurable console level
**Campaign Data**: Stored in `models/campaigns.json` and `models/knowledge/` directory

---

## ✨ Summary

A well-architected Gradio web app with modern design. Main strengths: builder pattern, status messages, campaign context. Main opportunities: form validation, progress visualization, accessibility, settings reorganization.

**Status**: Mature codebase ready for incremental UX improvements.

See `/UX_LANDSCAPE_ANALYSIS.md` for detailed analysis.
