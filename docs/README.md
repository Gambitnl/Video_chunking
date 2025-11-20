# Project Documentation Index

This directory contains all the documentation for the D&D Session Processor. Below is a summary of each file.

> **[ROCKET] New contributors**: Start with [`AGENT_ONBOARDING.md`](../AGENT_ONBOARDING.md) in the root directory for a structured onboarding path with step-by-step reading order.

---

### Core Documentation

- **[USAGE.md](./USAGE.md)**: The detailed user guide for all application features, both CLI and Web UI.
- **[QUICKREF.md](./QUICKREF.md)**: A one-page quick reference (cheatsheet) for common commands and configuration.
- **[PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md)**: A high-level summary of the project's features, architecture, and technology stack.

### Setup & Installation

- **[SETUP.md](./SETUP.md)**: The complete and detailed setup instructions for the application, including HF token setup and GPU (`INFERENCE_DEVICE`) guidance.
- **[FIRST_TIME_SETUP.md](./FIRST_TIME_SETUP.md)**: A quick-start guide for setting up the application and its dependencies for the first time.
- **[OLLAMA_SETUP.md](./OLLAMA_SETUP.md)**: A guide for installing Ollama, downloading the required LLM models, and tuning `OLLAMA_MODEL` (plus optional `OLLAMA_FALLBACK_MODEL`) to match your available memory.
- **[INSTALL_GPT_OSS.md](./INSTALL_GPT_OSS.md)**: Setup guide specifically for the OpenAI GPT-OSS model with Ollama.
- **[GOOGLE_DRIVE_SETUP.md](./GOOGLE_DRIVE_SETUP.md)**: Instructions for setting up Google Drive OAuth to access private Google Docs.
- **[GOOGLE_OAUTH_SIMPLE_SETUP.md](./GOOGLE_OAUTH_SIMPLE_SETUP.md)**: A streamlined walkthrough for generating Google OAuth credentials and enabling one-click authentication.
- **[INSTALLATION_STATUS.md](./INSTALLATION_STATUS.md)**: A checklist showing the installation status of all required dependencies.

### Feature Guides

- **[CAMPAIGN_DASHBOARD.md](./CAMPAIGN_DASHBOARD.md)**: A guide to the Campaign Dashboard, which provides a health check for your campaign configuration.
- **[CAMPAIGN_KNOWLEDGE_BASE.md](./CAMPAIGN_KNOWLEDGE_BASE.md)**: Explains the automatic knowledge base feature, which extracts quests, NPCs, and more from sessions.
- **[CHARACTER_PROFILES.md](./CHARACTER_PROFILES.md)**: A comprehensive guide to the Character Profile system, including tracking development and automatic data extraction.
- **[PARTY_CONFIG.md](./PARTY_CONFIG.md)**: Explains how to use Party Configurations to manage character and player information.
- **[SESSION_NOTEBOOK.md](./SESSION_NOTEBOOK.md)**: A guide to the Story Notebooks feature for generating narrative summaries from transcripts.
- **[STATUS_INDICATORS.md](./STATUS_INDICATORS.md)**: A reference guide for all status indicators, icons, and symbols used throughout the application.
- **[COLAB_OFFLOAD_PLAN.md](./COLAB_OFFLOAD_PLAN.md)**: Detailed plan for running the heavy GPU stages in Google Colab, including prep scripts, notebook flow, and sync steps.
- **[INTERMEDIATE_OUTPUTS_GUIDE.md](./INTERMEDIATE_OUTPUTS_GUIDE.md)**: Describes each intermediate JSON artifact (stages 4-6), how to edit them safely, and how resume processing consumes those files.
- **[SESSION_ARTIFACT_EXPLORER.md](./SESSION_ARTIFACT_EXPLORER.md)**: A guide to the Session Artifact Explorer, a UI for browsing, previewing, and downloading session output files.
- **[SESSION_ARTIFACT_SERVICE_STATUS.md](./SESSION_ARTIFACT_SERVICE_STATUS.md)**: Implementation status plus API, validation, and testing details for the backend powering the Session Artifact Explorer.

### Model References

- **[PYANNOTE_MODELS.md](./PYANNOTE_MODELS.md)**: Summaries of the gated pyannote segmentation and diarization releases, including access requirements and benchmark highlights.

### Development & Agent Workflows

- **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)**: A guide to common problems and their solutions.
- **[LOGGING_GUIDE.md](./LOGGING_GUIDE.md)**: Reference for runtime logging controls and the audit trail.

- **[CLAUDE.md](../CLAUDE.md)**: (In root) **AI ASSISTANT GUIDE** - Comprehensive reference for AI assistants (Claude, GPT, Gemini) working with this codebase. Covers structure, workflows, conventions, testing, and common tasks.
- **[AGENT_ONBOARDING.md](../AGENT_ONBOARDING.md)**: (In root) **START HERE** - Comprehensive onboarding guide with structured reading path for new AI agents and contributors. Tells you what to read and in what order.
- **[DEVELOPMENT.md](./DEVELOPMENT.md)**: A development chronicle logging major implementation and refactoring sessions.
- **[DIARIZATION_CLASSIFICATION_HISTORY.md](./DIARIZATION_CLASSIFICATION_HISTORY.md)**: Pipeline history focused on Stage 5/6 diarization and IC/OOC classification issues, mitigations, and pending work.
- **[archive/OUTSTANDING_TASKS.md](./archive/OUTSTANDING_TASKS.md)**: Backlog of prioritized tasks with the locking protocol for in-progress work.
- **[archive/BUG_HUNT_TODO.md](./archive/BUG_HUNT_TODO.md)**: Detailed bug hunt task list with context, issues, and reasoning notes (updated with Process Session progress tracking status on 2025-11-20).
- **[notes/inbox_20251120_classification_run.md](./notes/inbox_20251120_classification_run.md)**: Scratchpad TODOs from the 2025-11-20 log review (classification logging, model availability, and session list warnings).
- **[notes/live_review_implementation_plan.md](./notes/live_review_implementation_plan.md)**: Maximal implementation plan for live, in-process transcription/diarization/classification review with operator overrides and partial reruns.
- **[notes/knowledge_board_reimplementation.md](./notes/knowledge_board_reimplementation.md)**: Outline to recreate the knowledge board UI using our stack and data, without copying the Chronicler app code.
- **[notes/gradio_theme_toggle.md](./notes/gradio_theme_toggle.md)**: Draft plan for a toggle-able Chronicler-inspired theme in the Gradio Modern UI.

### Analysis & Technical Reviews

- **[IC_OOC_CLASSIFICATION_ANALYSIS.md](./IC_OOC_CLASSIFICATION_ANALYSIS.md)**: **MULTI-AGENT DISCUSSION** - Detailed analysis of IC/OOC classification quality, character attribution issues, and enhancement proposals (P0-P4). Structured for collaborative AI agent review and implementation planning.
- **[UI_STATUS.md](./UI_STATUS.md)**: A debugging and status guide for the Party Management UI tab.
- **[MASTER_PLAN.md](./MASTER_PLAN.md)**: The single source of truth for all open work items, sprint planning, and project status.
- **[CRITICAL_REVIEW_WORKFLOW.md](./CRITICAL_REVIEW_WORKFLOW.md)**: A step-by-step guide to the Critical Reviewer Agent methodology for rigorous code review with documented reasoning.
- **[CRITICAL_REVIEWER_SETUP_SUMMARY.md](./CRITICAL_REVIEWER_SETUP_SUMMARY.md)**: Summary of the Critical Reviewer Agent integration, including all files created/modified and how to use the system.
- **[AGENTS.md](../AGENTS.md)**: (In root) Core instructions for AI agents working in this repository, including Critical Reviewer invocation.
- **[CODEX.md](./CODEX.md)**: Guidance for the ChatGPT (Codex) agent covering identity checks, workflow expectations, and integration focus areas.
- **Operator Workflow**: See [AGENTS.md#operator-workflow](../AGENTS.md#operator-workflow) for the required plan -> implement -> document -> test loop that keeps implementation plans in sync.
- **[ROADMAP.md](../ROADMAP.md)**: (In root) Consolidated multi-agent roadmap covering priorities, ownership, and sequencing.
- **[COLLECTIVE_ROADMAP.md](../COLLECTIVE_ROADMAP.md)**: (In root) The high-level project plan and agent priorities.
- **[REFACTORING_PLAN.md](../REFACTORING_PLAN.md)**: (In root) The detailed plan for improving the codebase architecture.
- **[ROADMAP_VERIFICATION.md](./ROADMAP_VERIFICATION.md)**: Cross-document checklist verifying roadmap items against agent artifacts.
- **[CHATGPT_CODEX_REVIEW.md](./CHATGPT_CODEX_REVIEW.md)**: A code review and improvement plan logged by the ChatGPT (Codex) agent, now noting an incremental config auto-fill idea in the implementation plan.
- **[CLAUDE_SONNET_45_ANALYSIS.md](./CLAUDE_SONNET_45_ANALYSIS.md)**: A deep-dive analysis, bug report, and feature implementation log by the Claude (Sonnet 4.5) agent.
- **[GEMINI_CODE_REVIEW.md](./GEMINI_CODE_REVIEW.md)**: An initial code review and phased improvement plan from the Gemini agent.
- **[GEMINI_FEATURE_PROPOSAL.md](./GEMINI_FEATURE_PROPOSAL.md)**: A list of new feature proposals, bug detections, and visualization concepts from the Gemini agent.
