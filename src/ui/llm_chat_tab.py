from __future__ import annotations

import json
from pathlib import Path

import gradio as gr

from src.config import Config
from src.ui.helpers import Placeholders, InfoText, StatusMessages, UIComponents
from src.ui.constants import StatusIndicators as SI


def create_llm_chat_tab(project_root: Path) -> None:
    try:
        with open(project_root / "models" / "character_profiles.json", "r", encoding="utf-8") as handle:
            character_profiles = json.load(handle)
        character_names = ["None"] + list(character_profiles.keys())
    except (FileNotFoundError, json.JSONDecodeError):
        character_profiles = {}
        character_names = ["None"]

    def chat_with_llm(message: str, chat_history: list, character_name: str):
        try:
            import ollama

            client = ollama.Client(host="http://localhost:11434")
            ollama_messages = []

            if character_name and character_name != "None":
                profile = character_profiles.get(character_name)
                if profile:
                    system_prompt = (
                        f"You are role-playing as the character '{profile['name']}'. "
                        f"Description: {profile.get('description', 'N/A')}. "
                        f"Personality: {profile.get('personality', 'N/A')}. "
                        f"Backstory: {profile.get('backstory', 'N/A')}. "
                        "Stay in character and respond as they would."
                    )
                    ollama_messages.append({"role": "system", "content": system_prompt})

            ollama_messages.extend(chat_history)
            ollama_messages.append({"role": "user", "content": message})

            stream = client.chat(
                model=Config.OLLAMA_MODEL,
                messages=ollama_messages,
                stream=True,
            )

            chat_history.append({"role": "user", "content": message})
            chat_history.append({"role": "assistant", "content": ""})

            for chunk in stream:
                content = chunk["message"]["content"]
                if content:
                    chat_history[-1]["content"] += content
                    yield chat_history

        except Exception as exc:
            import traceback
            error_details = traceback.format_exc()

            error_msg = StatusMessages.error(
                "LLM Response Failed",
                "Unable to get a response from the language model.",
                f"{str(exc)}\n\nStack trace:\n{error_details}"
            )
            chat_history.append({"role": "assistant", "content": error_msg})
            yield chat_history

    with gr.Tab("LLM Chat"):
        gr.Markdown("""
        ### Chat with the Local LLM

        Interact with the configured Ollama model, optionally as a specific character.
        """)

        with gr.Row():
            character_dropdown = gr.Dropdown(
                label="Chat as Character",
                choices=character_names,
                value="None",
                info="Select a character to role-play as.",
            )

        chatbot = gr.Chatbot(label="Chat History", type="messages", height=600)
        msg = gr.Textbox(
            label="Your Message",
            placeholder=Placeholders.CAMPAIGN_QUESTION,
            lines=2
        )
        clear = gr.Button(f"{SI.ACTION_CLEAR} Chat")

        character_dropdown.change(lambda: [], None, [chatbot, msg])
        msg.submit(chat_with_llm, [msg, chatbot, character_dropdown], chatbot)
        clear.click(lambda: [], None, [chatbot, msg])
