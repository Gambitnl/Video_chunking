"""Campaign Chat Tab - Conversational interface for querying campaign data."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Dict

import gradio as gr

from src.config import Config

logger = logging.getLogger("DDSessionProcessor.campaign_chat_tab")


def create_campaign_chat_tab(project_root: Path) -> None:
    """Create the Campaign Chat tab for conversational campaign queries."""

    # Initialize conversation store
    from src.langchain.conversation_store import ConversationStore

    conversations_dir = project_root / "conversations"
    conv_store = ConversationStore(conversations_dir)

    # Track current conversation
    current_conversation_id = None

    def initialize_chat_client():
        """Initialize the chat client with retriever."""
        try:
            from src.langchain.campaign_chat import CampaignChatClient
            from src.langchain.retriever import CampaignRetriever

            # Set up retriever
            kb_dir = project_root / "models"
            transcript_dir = project_root / "output"

            retriever = CampaignRetriever(
                knowledge_base_dir=kb_dir,
                transcript_dir=transcript_dir
            )

            # Initialize chat client
            client = CampaignChatClient(retriever=retriever)

            return client, retriever

        except Exception as e:
            logger.error(f"Error initializing chat client: {e}", exc_info=True)
            return None, None

    chat_client, retriever = initialize_chat_client()

    def new_conversation():
        """Create a new conversation."""
        nonlocal current_conversation_id

        try:
            current_conversation_id = conv_store.create_conversation()
            logger.info(f"Created new conversation: {current_conversation_id}")

            # Clear chat client memory if available
            if chat_client:
                chat_client.clear_memory()

            return [], "", update_conversation_dropdown()

        except Exception as e:
            logger.error(f"Error creating new conversation: {e}", exc_info=True)
            return [], f"Error creating conversation: {e}", gr.update()

    def load_conversation(conversation_id: str):
        """Load an existing conversation."""
        nonlocal current_conversation_id

        if not conversation_id:
            return [], "", "Select a conversation to load"

        try:
            current_conversation_id = conversation_id
            chat_history = conv_store.get_chat_history(conversation_id)

            logger.info(f"Loaded conversation: {conversation_id}")

            # Clear chat client memory
            if chat_client:
                chat_client.clear_memory()

            return chat_history, "", ""

        except Exception as e:
            logger.error(f"Error loading conversation: {e}", exc_info=True)
            return [], "", f"Error loading conversation: {e}"

    def send_message(message: str, chat_history: List[Dict]):
        """Send a message and get a response."""
        nonlocal current_conversation_id

        if not message or not message.strip():
            return chat_history, ""

        # Create new conversation if none exists
        if not current_conversation_id:
            current_conversation_id = conv_store.create_conversation()

        try:
            # Add user message to history and store
            chat_history.append({"role": "user", "content": message})
            conv_store.add_message(
                current_conversation_id,
                role="user",
                content=message
            )

            # Get response from chat client
            if chat_client:
                response = chat_client.ask(message)
                answer = response["answer"]
                sources = response.get("sources", [])

                # Add assistant message to history and store
                chat_history.append({"role": "assistant", "content": answer})
                conv_store.add_message(
                    current_conversation_id,
                    role="assistant",
                    content=answer,
                    sources=sources
                )

                logger.info(f"Generated response with {len(sources)} sources")
            else:
                error_msg = "Chat client not initialized. Please check LangChain installation."
                chat_history.append({"role": "assistant", "content": error_msg})
                conv_store.add_message(
                    current_conversation_id,
                    role="assistant",
                    content=error_msg
                )

            return chat_history, ""

        except Exception as e:
            logger.error(f"Error sending message: {e}", exc_info=True)
            error_msg = f"Error: {str(e)}"
            chat_history.append({"role": "assistant", "content": error_msg})

            return chat_history, ""

    def update_conversation_dropdown():
        """Update the conversation dropdown with latest conversations."""
        try:
            conversations = conv_store.list_conversations(limit=20)

            choices = [
                f"{conv['conversation_id']} ({conv['message_count']} msgs) - {conv['campaign']}"
                for conv in conversations
            ]

            if not choices:
                return gr.update(choices=["No conversations yet"], value=None)

            return gr.update(choices=choices, value=None)

        except Exception as e:
            logger.error(f"Error updating conversation dropdown: {e}", exc_info=True)
            return gr.update(choices=["Error loading conversations"], value=None)

    def format_sources_display(chat_history: List[Dict]) -> str:
        """Format sources from the last assistant message."""
        if not chat_history:
            return "No sources yet"

        # Get the last assistant message
        last_assistant_msg = None
        for msg in reversed(chat_history):
            if msg["role"] == "assistant":
                last_assistant_msg = msg
                break

        if not last_assistant_msg or not current_conversation_id:
            return "No sources for this message"

        # Load full conversation to get sources
        conversation = conv_store.load_conversation(current_conversation_id)
        if not conversation:
            return "Error loading sources"

        # Find the corresponding message with sources
        for msg in reversed(conversation.get("messages", [])):
            if msg["role"] == "assistant" and msg["content"] == last_assistant_msg["content"]:
                sources = msg.get("sources", [])
                if not sources:
                    return "No sources cited for this answer"

                # Format sources
                sources_md = "### Sources\n\n"
                for i, source in enumerate(sources, 1):
                    content = source.get("content", "")
                    metadata = source.get("metadata", {})
                    source_type = metadata.get("type", "unknown")

                    if source_type == "transcript":
                        session_id = metadata.get("session_id", "Unknown")
                        timestamp = metadata.get("timestamp", "??:??:??")
                        speaker = metadata.get("speaker", "Unknown")
                        sources_md += f"**{i}. Transcript [{session_id}, {timestamp}]**\n"
                        sources_md += f"*{speaker}:* {content}\n\n"
                    else:
                        name = metadata.get("name", "Unknown")
                        sources_md += f"**{i}. {source_type.title()}: {name}**\n"
                        sources_md += f"{content}\n\n"

                return sources_md

        return "No sources available"

    # Create the UI
    with gr.Tab("Campaign Chat"):
        gr.Markdown("""
        ### 🗨️ Campaign Assistant

        Ask questions about your campaign, sessions, NPCs, quests, and more!

        **Examples:**
        - "What happened in the last session?"
        - "Who is the Shadow Lord?"
        - "When did Thorin get his magic sword?"
        - "Summarize the Crimson Peak arc"
        """)

        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="Campaign Assistant",
                    height=500,
                    type="messages",
                    show_label=True
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        label="Ask a question",
                        placeholder="What happened in session 5?",
                        scale=4,
                        lines=2
                    )
                    send_btn = gr.Button("Send", scale=1, variant="primary")

                with gr.Row():
                    clear_btn = gr.Button("Clear Chat", size="sm")
                    new_conv_btn = gr.Button("New Conversation", size="sm", variant="primary")

            with gr.Column(scale=1):
                gr.Markdown("### Conversations")
                conversation_dropdown = gr.Dropdown(
                    label="Load Previous",
                    choices=["No conversations yet"],
                    value=None,
                    interactive=True
                )

                load_conv_btn = gr.Button("Load Selected", size="sm")

                gr.Markdown("---")

                sources_display = gr.Markdown(
                    "No sources yet",
                    label="Sources"
                )

        # Event handlers
        send_btn.click(
            fn=send_message,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input]
        ).then(
            fn=format_sources_display,
            inputs=[chatbot],
            outputs=[sources_display]
        )

        msg_input.submit(
            fn=send_message,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input]
        ).then(
            fn=format_sources_display,
            inputs=[chatbot],
            outputs=[sources_display]
        )

        clear_btn.click(
            fn=lambda: ([], "No sources yet"),
            outputs=[chatbot, sources_display]
        )

        new_conv_btn.click(
            fn=new_conversation,
            outputs=[chatbot, msg_input, conversation_dropdown]
        ).then(
            fn=lambda: "New conversation started",
            outputs=[sources_display]
        )

        load_conv_btn.click(
            fn=lambda dropdown_val: load_conversation(
                dropdown_val.split(" ")[0] if dropdown_val else None
            ),
            inputs=[conversation_dropdown],
            outputs=[chatbot, msg_input, sources_display]
        )

        # Update conversation list on tab load
        gr.on(
            triggers=[send_btn.click, new_conv_btn.click],
            fn=update_conversation_dropdown,
            outputs=[conversation_dropdown]
        )

        # Initialize
        if not chat_client:
            gr.Markdown("""
            ⚠️ **Warning:** LangChain dependencies not installed.

            To use this feature, install:
            ```bash
            pip install langchain langchain-community sentence-transformers chromadb
            ```
            """)
