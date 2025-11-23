"""Modern theme configuration for Gradio UI."""
import gradio as gr

# Modern color palette
COLORS = {
    # Primary brand colors
    "primary": "#6366f1",  # Indigo
    "primary_hover": "#4f46e5",
    "primary_light": "#818cf8",

    # Accent colors
    "accent": "#06b6d4",  # Cyan
    "success": "#10b981",  # Green
    "warning": "#f59e0b",  # Amber
    "error": "#ef4444",  # Red
    "info": "#3b82f6",  # Blue

    # Neutral colors (light mode)
    "background": "#ffffff",
    "surface": "#f9fafb",
    "surface_elevated": "#ffffff",
    "border": "#e5e7eb",
    "text_primary": "#111827",
    "text_secondary": "#6b7280",
    "text_tertiary": "#9ca3af",

    # Dark mode neutrals
    "dark_background": "#0f172a",
    "dark_surface": "#1e293b",
    "dark_surface_elevated": "#334155",
    "dark_border": "#334155",
    "dark_text_primary": "#f1f5f9",
    "dark_text_secondary": "#cbd5e1",
}

# Custom CSS for modern look
MODERN_CSS = """
/* Global styles */
.gradio-container {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
    max-width: 100% !important;
    padding: 0 2rem !important;
    margin: 0 auto !important;
}

/* Tab styling */
.tabs {
    border-bottom: 2px solid #e5e7eb;
}

.tab-nav button {
    font-size: 0.95rem;
    font-weight: 500;
    padding: 0.75rem 1.5rem;
    border: none;
    background: transparent;
    color: #6b7280;
    transition: all 0.2s;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
}

.tab-nav button:hover {
    color: #111827;
    background: #f9fafb;
}

.tab-nav button.selected {
    color: #6366f1;
    border-bottom-color: #6366f1;
    background: transparent;
}

/* Fix tab content width consistency - force all tabs to expand to full width */
.gradio-container {
    min-width: 1200px !important;
}

/* Ensure all tab panels take full width of container */
.tabitem {
    min-width: 100% !important;
    width: 100% !important;
}

/* Force tab content to expand */
.tabitem > div {
    min-width: 100% !important;
}

/* Prevent container from collapsing based on content */
.tabs {
    width: 100% !important;
    min-width: 100% !important;
}

/* Ensure markdown and other components expand to fill tab */
.tabitem .markdown,
.tabitem .block,
.tabitem > div > div {
    width: 100% !important;
    box-sizing: border-box;
}

/* Card styling for sections */
.card {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    border: 1px solid #e5e7eb;
    box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
    margin-bottom: 1rem;
}

/* Button improvements */
.btn-primary {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
    border: none;
    border-radius: 8px;
    padding: 0.625rem 1.25rem;
    font-weight: 500;
    font-size: 0.95rem;
    color: white;
    transition: all 0.2s;
    box-shadow: 0 1px 3px 0 rgb(99 102 241 / 0.4);
}

.btn-primary:hover {
    background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
    box-shadow: 0 4px 6px -1px rgb(99 102 241 / 0.4);
    transform: translateY(-1px);
}

.btn-secondary {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 0.625rem 1.25rem;
    font-weight: 500;
    font-size: 0.95rem;
    color: #374151;
    transition: all 0.2s;
}

.btn-secondary:hover {
    background: #f9fafb;
    border-color: #d1d5db;
}

/* Input field improvements */
input[type="text"],
input[type="file"],
textarea,
select {
    border-radius: 8px !important;
    border: 1px solid #e5e7eb !important;
    padding: 0.625rem 0.875rem !important;
    font-size: 0.95rem !important;
    transition: all 0.2s !important;
}

input[type="text"]:focus,
textarea:focus,
select:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgb(99 102 241 / 0.1) !important;
    outline: none !important;
}

/* File upload styling */
.file-upload {
    border: 2px dashed #d1d5db;
    border-radius: 12px;
    padding: 2rem;
    text-align: center;
    transition: all 0.2s;
    background: #f9fafb;
}

.file-upload:hover {
    border-color: #6366f1;
    background: #f0f1ff;
}

/* Progress bar */
.progress-bar {
    height: 8px;
    border-radius: 9999px;
    background: #e5e7eb;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #6366f1 0%, #06b6d4 100%);
    transition: width 0.3s ease;
}

/* Collapsible sections - Accordion styling */
.accordion {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 1rem;
}

.accordion-header {
    padding: 1rem 1.25rem;
    background: #f9fafb;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 500;
    transition: all 0.2s;
}

.accordion-header:hover {
    background: #f3f4f6;
}

.accordion-content {
    padding: 1.25rem;
    border-top: 1px solid #e5e7eb;
}

/* Gradio accordion (details/summary) improvements */
details summary {
    padding: 0.875rem 1.125rem !important;
    background: #f9fafb !important;
    border-radius: 8px !important;
    border: 1px solid #e5e7eb !important;
    cursor: pointer !important;
    font-weight: 500 !important;
    transition: all 0.2s !important;
    list-style: none !important;
}

details summary::-webkit-details-marker {
    display: none !important;
}

details summary::before {
    content: "▶" !important;
    display: inline-block !important;
    margin-right: 0.75rem !important;
    transition: transform 0.2s !important;
    color: #6366f1 !important;
    font-size: 0.75rem !important;
}

details[open] summary::before {
    transform: rotate(90deg) !important;
}

details summary:hover {
    background: #f3f4f6 !important;
    border-color: #d1d5db !important;
}

details[open] summary {
    border-bottom-left-radius: 0 !important;
    border-bottom-right-radius: 0 !important;
    border-bottom: none !important;
}

details > div {
    border: 1px solid #e5e7eb !important;
    border-top: none !important;
    border-bottom-left-radius: 8px !important;
    border-bottom-right-radius: 8px !important;
    padding: 1.25rem !important;
}

/* Info tooltips */
.info-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #e5e7eb;
    color: #6b7280;
    font-size: 12px;
    font-weight: 600;
    cursor: help;
    margin-left: 0.5rem;
}

.info-icon:hover {
    background: #6366f1;
    color: white;
}

/* Status badges */
.badge {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.875rem;
    font-weight: 500;
}

.badge-success {
    background: #d1fae5;
    color: #065f46;
}

.badge-warning {
    background: #fef3c7;
    color: #92400e;
}

.badge-error {
    background: #fee2e2;
    color: #991b1b;
}

.badge-info {
    background: #dbeafe;
    color: #1e40af;
}

/* Workflow stepper */
.stepper {
    display: flex;
    align-items: center;
    margin-bottom: 2rem;
    padding: 1.5rem;
    background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
    border-radius: 12px;
}

.step {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
    position: relative;
}

.step-number {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: #e5e7eb;
    color: #6b7280;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 1.125rem;
    margin-bottom: 0.5rem;
}

.step.active .step-number {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
    color: white;
    box-shadow: 0 4px 6px -1px rgb(99 102 241 / 0.4);
}

.step.completed .step-number {
    background: #10b981;
    color: white;
}

.step-label {
    font-size: 0.875rem;
    font-weight: 500;
    color: #6b7280;
}

.step.active .step-label {
    color: #6366f1;
    font-weight: 600;
}

.step-connector {
    position: absolute;
    top: 20px;
    left: 50%;
    width: 100%;
    height: 2px;
    background: #e5e7eb;
    z-index: -1;
}

.step.completed .step-connector {
    background: #10b981;
}

/* Markdown content improvements */
.markdown-content h1 {
    font-size: 1.875rem;
    font-weight: 700;
    margin-bottom: 1rem;
    color: #111827;
}

.markdown-content h2 {
    font-size: 1.5rem;
    font-weight: 600;
    margin-top: 2rem;
    margin-bottom: 1rem;
    color: #111827;
}

.markdown-content h3 {
    font-size: 1.25rem;
    font-weight: 600;
    margin-top: 1.5rem;
    margin-bottom: 0.75rem;
    color: #374151;
}

.markdown-content p {
    line-height: 1.75;
    color: #4b5563;
    margin-bottom: 1rem;
}

.markdown-content code {
    background: #f3f4f6;
    padding: 0.125rem 0.375rem;
    border-radius: 0.25rem;
    font-size: 0.875em;
    color: #6366f1;
}

/* Loading states */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.loading {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* Scrollbar styling */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: #f9fafb;
}

::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
}

/* Campaign Badge - Sticky header showing active campaign */
.campaign-badge-sticky {
    position: sticky;
    top: 0;
    z-index: 100;
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
    color: white !important;
    padding: 0.75rem 1rem;
    text-align: center;
    border-radius: 8px;
    margin-bottom: 1rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.campaign-badge-sticky p {
    margin: 0 !important;
    color: white !important;
    font-weight: 600;
    font-size: 1rem;
}

.campaign-badge-sticky strong {
    color: white !important;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .stepper {
        flex-direction: column;
    }

    .step-connector {
        display: none;
    }

    .gradio-container {
        padding: 1rem;
    }
}

/* Event Log Styling */
.event-log-textbox {
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace !important;
    font-size: 0.85rem !important;
    line-height: 1.6 !important;
    background-color: #1e1e1e !important;
    color: #d4d4d4 !important;
    border-radius: 8px !important;
    padding: 1rem !important;
}

.event-log-textbox textarea {
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace !important;
    font-size: 0.85rem !important;
    line-height: 1.6 !important;
    background-color: #1e1e1e !important;
    color: #d4d4d4 !important;
    scrollbar-width: thin;
    scrollbar-color: #4a4a4a #1e1e1e;
}

.event-log-textbox textarea::-webkit-scrollbar {
    width: 8px;
}

.event-log-textbox textarea::-webkit-scrollbar-track {
    background: #1e1e1e;
    border-radius: 4px;
}

.event-log-textbox textarea::-webkit-scrollbar-thumb {
    background: #4a4a4a;
    border-radius: 4px;
}

.event-log-textbox textarea::-webkit-scrollbar-thumb:hover {
    background: #5a5a5a;
}

/* Stage Progress Styling */
.stage-progress-display {
    background: #f9fafb;
    border-radius: 8px;
    padding: 1rem;
    border-left: 4px solid #6366f1;
}

/* Empty State Cards */
.empty-state-card {
    background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
    border: 2px dashed #d1d5db;
    border-radius: 12px;
    padding: 3rem 2rem;
    text-align: center;
    margin: 2rem 0;
}

.empty-state-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
    line-height: 1;
}

.empty-state-card h3 {
    font-size: 1.5rem;
    font-weight: 600;
    color: #374151;
    margin-bottom: 0.75rem;
}

.empty-state-card p {
    font-size: 1rem;
    color: #6b7280;
    margin-bottom: 1.5rem;
    line-height: 1.6;
}

.empty-state-actions {
    display: flex;
    gap: 1rem;
    justify-content: center;
    flex-wrap: wrap;
}

.empty-state-card .info-badge {
    display: inline-block;
    background: #dbeafe;
    color: #1e40af;
    padding: 0.5rem 1rem;
    border-radius: 9999px;
    font-size: 0.875rem;
    font-weight: 500;
    margin: 0.25rem;
}
"""

def create_modern_theme():
    """Create a modern Gradio theme."""
    return gr.themes.Soft(
        primary_hue="indigo",
        secondary_hue="cyan",
        neutral_hue="slate",
    )
