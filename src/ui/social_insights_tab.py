from __future__ import annotations

import gradio as gr


def create_social_insights_tab() -> None:
    def analyze_ooc_ui(session_id):
        try:
            from src.analyzer import OOCAnalyzer
            from src.config import Config
            from wordcloud import WordCloud

            if not session_id:
                return "Please enter a session ID.", None

            from src.formatter import sanitize_filename

            sanitized_session_id = sanitize_filename(session_id)
            ooc_file = Config.OUTPUT_DIR / f"{sanitized_session_id}_ooc_only.txt"
            if not ooc_file.exists():
                return f"OOC transcript not found for session: {session_id}", None

            analyzer = OOCAnalyzer(ooc_file)
            keywords = analyzer.get_keywords(top_n=30)

            if not keywords:
                return "No significant keywords found in the OOC transcript.", None

            wc = WordCloud(
                width=800,
                height=400,
                background_color="#0C111F",
                colormap="cool",
                max_words=100,
                contour_width=3,
                contour_color="#89DDF5",
            )
            wc.generate_from_frequencies(dict(keywords))

            temp_path = Config.TEMP_DIR / f"{sanitized_session_id}_nebula.png"
            wc.to_file(str(temp_path))

            keyword_md = "### Top Keywords\n\n| Rank | Keyword | Frequency |\n|---|---|---|"
            for idx, (word, count) in enumerate(keywords, 1):
                keyword_md += f"| {idx} | {word} | {count} |\n"

            return keyword_md, temp_path

        except Exception as exc:
            return f"Error during analysis: {exc}", None

    with gr.Tab("Social Insights"):
        gr.Markdown("""
        ### OOC Keyword Analysis (Topic Nebula)

        Analyze the out-of-character banter to find the most common topics and keywords.

        **Workflow**
        - Enter the session ID that matches the processed output folder (e.g., `session_2024_05_01`).
        - Click **Analyze Banter** to compute TF-IDF keywords from the saved OOC transcript and render the nebula word cloud.
        - If no OOC transcript exists yet, run the main pipeline first or verify the session ID matches the generated files.

        **Interpreting results**
        - The markdown table highlights the top terms with raw counts so you can skim popular jokes and topics.
        - The nebula graphic saves to `temp/` for reuse in retrospectives or recap decks.
        - Rerun the analysis after updating speaker mappings or classifications to compare topic shifts between sessions.
        """)
        with gr.Row():
            with gr.Column():
                insight_session_id = gr.Textbox(
                    label="Session ID",
                    placeholder="Enter the ID of a completed session",
                )
                insight_btn = gr.Button("[ANALYZE] Analyze Banter", variant="primary")
            with gr.Column():
                keyword_output = gr.Markdown(label="Top Keywords")
        with gr.Row():
            nebula_output = gr.Image(label="Topic Nebula")

        insight_btn.click(
            fn=analyze_ooc_ui,
            inputs=[insight_session_id],
            outputs=[keyword_output, nebula_output],
        )