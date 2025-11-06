"""Campaign Chat Tab - Conversational interface for querying campaign data."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Dict

import gradio as gr

from src.config import Config
from src.ui.helpers import StatusMessages, Placeholders
from src.ui.constants import StatusIndicators as SI

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

    def clear_chat():
        """Clear the chat UI and reset conversation state."""
        nonlocal current_conversation_id
        current_conversation_id = None

        # Clear chat client memory if available
        if chat_client:
            chat_client.clear_memory()

        logger.info("Chat cleared, conversation state reset")
        return [], f"{SI.INFO} Chat cleared - next message will start a new conversation"

    def new_conversation():
        """Create a new conversation."""
        nonlocal current_conversation_id

        try:
            current_conversation_id = conv_store.create_conversation()
            logger.info(f"Created new conversation: {current_conversation_id}")

            # Clear chat client memory if available
            if chat_client:
                chat_client.clear_memory()

            success_msg = f"{SI.SUCCESS} New conversation started: {current_conversation_id}"
            return [], "", update_conversation_dropdown(), success_msg

        except Exception as e:
            logger.error(f"Error creating new conversation: {e}", exc_info=True)
            error_msg = StatusMessages.error(
                "Conversation Creation Failed",
                "Unable to create a new conversation.",
                str(e)
            )
            return [], "", gr.update(), error_msg

    def load_conversation(conversation_id: str):
        """Load an existing conversation."""
        nonlocal current_conversation_id

        if not conversation_id:
            info_msg = f"{SI.INFO} Select a conversation to load"
            return [], "", info_msg

        try:
            current_conversation_id = conversation_id
            chat_history = conv_store.get_chat_history(conversation_id)

            logger.info(f"Loaded conversation: {conversation_id}")

            # Clear chat client memory
            if chat_client:
                chat_client.clear_memory()

            success_msg = f"{SI.SUCCESS} Loaded conversation: {conversation_id} ({len(chat_history)} messages)"
            return chat_history, "", success_msg

        except Exception as e:
            logger.error(f"Error loading conversation: {e}", exc_info=True)
            error_msg = StatusMessages.error(
                "Load Failed",
                "Unable to load the selected conversation.",
                str(e)
            )
            return [], "", error_msg

    def send_message_show_loading(message: str, chat_history: List[Dict]):
        """First step: Add user message and show loading indicator."""
        nonlocal current_conversation_id

        if not message or not message.strip():
            return chat_history, "", gr.update(), StatusMessages.info("Ready", "Type a message to start")

        try:
            # Create new conversation if none exists
            if not current_conversation_id:
                current_conversation_id = conv_store.create_conversation()

            # Add user message to history and store
            chat_history.append({"role": "user", "content": message})
            conv_store.add_message(
                current_conversation_id,
                role="user",
                content=message
            )

            # Show loading indicator with better UX
            loading_msg = f"{SI.LOADING} 🤔 Thinking... (querying campaign data)"

            return chat_history, "", gr.update(), loading_msg

        except Exception as e:
            logger.error(f"Error in send_message_show_loading: {e}", exc_info=True)
            error_msg = StatusMessages.error(
                "Message Setup Failed",
                "Unable to send your message. Please try again.",
                "Error details have been logged for troubleshooting."
            )
            return chat_history, "", gr.update(), error_msg

    def send_message_get_response(chat_history: List[Dict]):
        """Second step: Get LLM response and update chat."""
        nonlocal current_conversation_id

        if not current_conversation_id:
            error_msg = StatusMessages.error(
                "No Conversation",
                "No active conversation found."
            )
            chat_history.append({"role": "assistant", "content": error_msg})
            return chat_history, gr.update()

        try:
            # Get response from chat client
            if chat_client:
                # Get the last user message
                last_user_msg = None
                for msg in reversed(chat_history):
                    if msg["role"] == "user":
                        last_user_msg = msg["content"]
                        break

                if not last_user_msg:
                    error_msg = StatusMessages.error("No Message", "Could not find user message.")
                    chat_history.append({"role": "assistant", "content": error_msg})
                    conv_store.add_message(
                        current_conversation_id,
                        role="assistant",
                        content=error_msg
                    )
                    return chat_history, gr.update()

                response = chat_client.ask(last_user_msg)
                answer = response["answer"]
                sources = response.get("sources", [])

                # Add assistant response to history and store
                chat_history.append({"role": "assistant", "content": answer})
                conv_store.add_message(
                    current_conversation_id,
                    role="assistant",
                    content=answer,
                    sources=sources
                )

                logger.info(f"Generated response with {len(sources)} sources")
                # Return chat_history so format_sources_display can show sources
                return chat_history, update_conversation_dropdown()

            else:
                error_msg = StatusMessages.error(
                    "Chat Client Not Available",
                    "The chat client is not initialized. Please check LangChain installation.",
                    "Install: pip install langchain langchain-community sentence-transformers chromadb"
                )
                chat_history.append({"role": "assistant", "content": error_msg})
                conv_store.add_message(
                    current_conversation_id,
                    role="assistant",
                    content=error_msg
                )
                return chat_history, gr.update()

        except Exception as e:
            logger.error(f"Error getting LLM response: {e}", exc_info=True)
            error_msg = StatusMessages.error(
                "Message Send Failed",
                "Unable to process your message.",
                str(e)
            )
            chat_history.append({"role": "assistant", "content": error_msg})
            conv_store.add_message(
                current_conversation_id,
                role="assistant",
                content=error_msg
            )
            return chat_history, gr.update()

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
            return f"{SI.INFO} No sources yet"

        # Get the last assistant message
        last_assistant_msg = None
        for msg in reversed(chat_history):
            if msg["role"] == "assistant":
                last_assistant_msg = msg
                break

        if not last_assistant_msg:
            return f"{SI.INFO} No assistant messages yet"

        # Check if the message is an error message (starts with ### [ERROR])
        if last_assistant_msg["content"].startswith("### [ERROR]"):
            return f"{SI.INFO} No sources (error message)"

        # Check if no conversation exists
        if not current_conversation_id:
            return f"{SI.INFO} No active conversation"

        # Load full conversation to get sources
        try:
            conversation = conv_store.load_conversation(current_conversation_id)
            if not conversation:
                return f"{SI.WARNING} Could not load conversation data"

            # Find the corresponding message with sources
            # Match by position (last assistant message) rather than content
            assistant_messages = [
                msg for msg in conversation.get("messages", [])
                if msg["role"] == "assistant"
            ]

            if not assistant_messages:
                return f"{SI.INFO} No messages in conversation"

            # Get the last assistant message from stored conversation
            last_stored_msg = assistant_messages[-1]
            sources = last_stored_msg.get("sources", [])

            if not sources:
                return f"{SI.INFO} No sources cited for this answer"

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

        except Exception as e:
            logger.error(f"Error formatting sources: {e}", exc_info=True)
            return f"{SI.ERROR} Error loading sources"

    # Create the UI
    with gr.Tab("Campaign Chat"):
        gr.Markdown("""
        ### [CHAT] Campaign Assistant

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
                    height=600,
                    type="messages",
                    show_label=True
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        label="Ask a question",
                        placeholder=Placeholders.CAMPAIGN_QUESTION,
                        scale=4,
                        lines=2
                    )
                    send_btn = gr.Button(SI.ACTION_SEND, scale=1, variant="primary")

        with gr.Row():
            clear_btn = gr.Button(f"{SI.ACTION_CLEAR} Chat", size="sm")
            new_conv_btn = gr.Button(f"{SI.ACTION_NEW} Conversation", size="sm", variant="primary")
            delete_btn = gr.Button(f"{SI.ACTION_DELETE} Selected", size="sm", variant="secondary")
            rename_btn = gr.Button(f"{SI.ACTION_EDIT} Rename", size="sm", variant="secondary")

            with gr.Column(scale=1):
                gr.Markdown("### Conversations")
                conversation_dropdown = gr.Dropdown(
                    label="Load Previous",
                    choices=["No conversations yet"],
                    value=None,
                    interactive=True
                )

                load_conv_btn = gr.Button(f"{SI.ACTION_LOAD} Selected", size="sm")

                gr.Markdown("---")

                sources_display = gr.Markdown(
                    "No sources yet",
                    label="Sources"
                )

        # Event handlers - Three-step pattern: show loading -> get response -> show sources
        send_btn.click(
            fn=send_message_show_loading,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input, conversation_dropdown, sources_display]
        ).then(
            fn=send_message_get_response,
            inputs=[chatbot],
            outputs=[chatbot, conversation_dropdown]
        ).then(
            fn=format_sources_display,
            inputs=[chatbot],
            outputs=[sources_display]
        )

        msg_input.submit(
            fn=send_message_show_loading,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input, conversation_dropdown, sources_display]
        ).then(
            fn=send_message_get_response,
            inputs=[chatbot],
            outputs=[chatbot, conversation_dropdown]
        ).then(
            fn=format_sources_display,
            inputs=[chatbot],
            outputs=[sources_display]
        )

        clear_btn.click(
            fn=clear_chat,
            outputs=[chatbot, sources_display]
        )

        new_conv_btn.click(
            fn=new_conversation,
            outputs=[chatbot, msg_input, conversation_dropdown, sources_display]
        )

        load_conv_btn.click(
            fn=lambda dropdown_val: load_conversation(
                dropdown_val.split(" ")[0] if dropdown_val else None
            ),
            inputs=[conversation_dropdown],
            outputs=[chatbot, msg_input, sources_display]
        )

        # Initialize
        if not chat_client:
            gr.Markdown("""
            [WARNING] **Warning:** LangChain dependencies not installed.

            To use this feature, install:
            ```bash
            pip install langchain langchain-community sentence-transformers chromadb
            ```
            """)
