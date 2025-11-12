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

### Model References

- **[PYANNOTE_MODELS.md](./PYANNOTE_MODELS.md)**: Summaries of the gated pyannote segmentation and diarization releases, including access requirements and benchmark highlights.

### Development & Agent Workflows

- **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)**: A guide to common problems and their solutions.
- **[LOGGING_GUIDE.md](./LOGGING_GUIDE.md)**: Reference for runtime logging controls and the audit trail.

- **[AGENT_ONBOARDING.md](../AGENT_ONBOARDING.md)**: (In root) **START HERE** - Comprehensive onboarding guide with structured reading path for new AI agents and contributors. Tells you what to read and in what order.
- **[DEVELOPMENT.md](./DEVELOPMENT.md)**: A development chronicle logging major implementation and refactoring sessions.
- **[UI_STATUS.md](./UI_STATUS.md)**: A debugging and status guide for the Party Management UI tab.
- **[MASTER_PLAN.md](./MASTER_PLAN.md)**: The single source of truth for all open work items, sprint planning, and project status.
- **[CRITICAL_REVIEW_WORKFLOW.md](./CRITICAL_REVIEW_WORKFLOW.md)**: A step-by-step guide to the Critical Reviewer Agent methodology for rigorous code review with documented reasoning.
- **[CRITICAL_REVIEWER_SETUP_SUMMARY.md](./CRITICAL_REVIEWER_SETUP_SUMMARY.md)**: Summary of the Critical Reviewer Agent integration, including all files created/modified and how to use the system.
- **[AGENTS.md](../AGENTS.md)**: (In root) Core instructions for AI agents working in this repository, including Critical Reviewer invocation.
- **Operator Workflow**: See [AGENTS.md#operator-workflow](../AGENTS.md#operator-workflow) for the required plan -> implement -> document -> test loop that keeps implementation plans in sync.
- **[ROADMAP.md](../ROADMAP.md)**: (In root) Consolidated multi-agent roadmap covering priorities, ownership, and sequencing.
- **[COLLECTIVE_ROADMAP.md](../COLLECTIVE_ROADMAP.md)**: (In root) The high-level project plan and agent priorities.
- **[REFACTORING_PLAN.md](../REFACTORING_PLAN.md)**: (In root) The detailed plan for improving the codebase architecture.
- **[ROADMAP_VERIFICATION.md](./ROADMAP_VERIFICATION.md)**: Cross-document checklist verifying roadmap items against agent artifacts.
- **[CHATGPT_CODEX_REVIEW.md](./CHATGPT_CODEX_REVIEW.md)**: A code review and improvement plan logged by the ChatGPT (Codex) agent, now noting an incremental config auto-fill idea in the implementation plan.
- **[CLAUDE_SONNET_45_ANALYSIS.md](./CLAUDE_SONNET_45_ANALYSIS.md)**: A deep-dive analysis, bug report, and feature implementation log by the Claude (Sonnet 4.5) agent.
- **[GEMINI_CODE_REVIEW.md](./GEMINI_CODE_REVIEW.md)**: An initial code review and phased improvement plan from the Gemini agent.
- **[GEMINI_FEATURE_PROPOSAL.md](./GEMINI_FEATURE_PROPOSAL.md)**: A list of new feature proposals, bug detections, and visualization concepts from the Gemini agent.
