
import os
from uuid import uuid4

import httpx
import streamlit as st


# -------------------- Backend configuration --------------------

try:
    API_URL = st.secrets["API_URL"]
except (KeyError, FileNotFoundError):
    API_URL = os.getenv("API_URL", "http://127.0.0.1:8001")

API_URL = API_URL.rstrip("/")


# -------------------- Page configuration --------------------

st.set_page_config(
    page_title="Genaibot | AI Document Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -------------------- Styling --------------------

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1100px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .hero {
        padding: 1.7rem;
        border-radius: 18px;
        background: linear-gradient(120deg, #172554, #334155);
        color: white;
        margin-bottom: 1.2rem;
    }

    .hero h1 {
        margin-bottom: 0.35rem;
    }

    .hero p {
        margin-bottom: 0;
        opacity: 0.92;
    }

    div[data-testid="stSidebar"] {
        border-right: 1px solid rgba(128, 128, 128, 0.2);
    }

    .stButton button {
        border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------- Session-state initialization --------------------

if "uploaded_documents" not in st.session_state:
    st.session_state.uploaded_documents = []

if "chat_sessions" not in st.session_state:
    first_chat_id = uuid4().hex
    st.session_state.chat_sessions = {
        first_chat_id: {
            "title": "New Chat",
            "messages": [],
        }
    }
    st.session_state.active_chat_id = first_chat_id

if (
    "active_chat_id" not in st.session_state
    or st.session_state.active_chat_id
    not in st.session_state.chat_sessions
):
    st.session_state.active_chat_id = next(
        iter(st.session_state.chat_sessions)
    )

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = False

if "document_selection" not in st.session_state:
    st.session_state.document_selection = "__none__"

if "chat_selector" not in st.session_state:
    st.session_state.chat_selector = st.session_state.active_chat_id
elif (
    st.session_state.chat_selector
    not in st.session_state.chat_sessions
):
    st.session_state.chat_selector = st.session_state.active_chat_id

if "rename_input" not in st.session_state:
    st.session_state.rename_input = st.session_state.chat_sessions[
        st.session_state.active_chat_id
    ]["title"]


# -------------------- Helpers --------------------

def display_citations(message):
    """Display supporting evidence returned by the RAG API."""

    citations = message.get("citations", []) or []
    sources = message.get("sources", []) or []

    if citations:
        with st.expander("📑 View supporting evidence"):
            for index, citation in enumerate(citations, start=1):
                filename = citation.get("filename", "Unknown document")
                chunk_index = citation.get("chunk_index", "Unknown")
                excerpt = citation.get("excerpt", "")

                st.markdown(
                    f"**Source {index}: `{filename}`**"
                )
                st.caption(f"Retrieved chunk: {chunk_index}")

                if excerpt:
                    st.markdown(f"> {excerpt}")

                if index < len(citations):
                    st.divider()

    elif sources:
        with st.expander("📑 View sources"):
            for source in sources:
                st.markdown(f"- `{source}`")


def create_new_chat():
    """Create a new independent conversation."""

    chat_id = uuid4().hex

    st.session_state.chat_sessions[chat_id] = {
        "title": "New Chat",
        "messages": [],
    }

    st.session_state.active_chat_id = chat_id
    st.session_state.chat_selector = chat_id
    st.session_state.rename_input = "New Chat"
    st.session_state.confirm_delete = False
    st.session_state.pending_question = None


def switch_chat():
    """Switch to the selected conversation."""

    chat_id = st.session_state.get("chat_selector")

    if chat_id in st.session_state.chat_sessions:
        st.session_state.active_chat_id = chat_id
        st.session_state.rename_input = (
            st.session_state.chat_sessions[chat_id]["title"]
        )
        st.session_state.confirm_delete = False
        st.session_state.pending_question = None


def confirm_delete_current_chat():
    """Delete the active chat and select a replacement."""

    chat_id = st.session_state.active_chat_id
    st.session_state.chat_sessions.pop(chat_id, None)

    if not st.session_state.chat_sessions:
        next_chat_id = uuid4().hex

        st.session_state.chat_sessions[next_chat_id] = {
            "title": "New Chat",
            "messages": [],
        }
    else:
        next_chat_id = next(iter(st.session_state.chat_sessions))

    st.session_state.active_chat_id = next_chat_id
    st.session_state.chat_selector = next_chat_id
    st.session_state.rename_input = (
        st.session_state.chat_sessions[next_chat_id]["title"]
    )
    st.session_state.confirm_delete = False
    st.session_state.pending_question = None


def cancel_delete_current_chat():
    """Cancel the pending chat deletion."""

    st.session_state.confirm_delete = False


def selected_document_label(option):
    """Provide readable labels for document-selector options."""

    if option == "__none__":
        return "No document selected"

    if option == "__all__":
        return "All documents"

    for document in st.session_state.uploaded_documents:
        if document.get("document_id") == option:
            return (
                f"{document['filename']} · {option[:6]}"
            )

    return str(option)


# -------------------- Sidebar: documents and chats --------------------

with st.sidebar:
    st.markdown("## 📚 Knowledge Base")

    st.caption(
        "Upload a PDF or TXT file, then select which document "
        "to ask about."
    )

    uploaded_file = st.file_uploader(
        "Choose a PDF or TXT file",
        type=["pdf", "txt"],
        help="Choose a document for Genaibot to read.",
        key="document_uploader",
    )

    if st.button(
        "Upload and index",
        disabled=uploaded_file is None,
        use_container_width=True,
        type="primary",
        key="upload_and_index",
    ):
        try:
            with st.spinner(
                "Reading and indexing your document..."
            ):
                file_data = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        uploaded_file.type
                        or "application/octet-stream",
                    )
                }

                response = httpx.post(
                    f"{API_URL}/upload",
                    files=file_data,
                    timeout=180.0,
                )

            if response.is_success:
                result = response.json()

                filename = result.get(
                    "filename",
                    uploaded_file.name,
                )
                document_id = result.get("document_id")
                chunks = result.get("chunks_indexed", 0)

                if not document_id:
                    st.error(
                        "The backend indexed the file but did not "
                        "return a document ID."
                    )
                else:
                    existing_ids = {
                        item.get("document_id")
                        for item in st.session_state.uploaded_documents
                    }

                    if document_id not in existing_ids:
                        st.session_state.uploaded_documents.append(
                            {
                                "filename": filename,
                                "document_id": document_id,
                                "chunks": chunks,
                            }
                        )

                    # Select the newly uploaded document automatically.
                    st.session_state.document_selection = document_id

                    st.success("Document indexed successfully!")
                    st.markdown(f"**File:** {filename}")
                    st.metric("Text chunks indexed", chunks)

            else:
                st.error(
                    f"Upload failed ({response.status_code}): "
                    f"{response.text[:400]}"
                )

        except httpx.RequestError as exc:
            st.error(
                "Couldn't reach the backend. "
                "Check that the API is running."
            )
            st.caption(str(exc)[:300])

    documents = st.session_state.uploaded_documents

    if documents:
        st.divider()
        st.markdown("### Answer using")

        document_options = ["__none__", "__all__"] + [
            item["document_id"]
            for item in documents
        ]

        if (
            st.session_state.document_selection
            not in document_options
        ):
            st.session_state.document_selection = "__none__"

        st.selectbox(
            "Choose a document",
            options=document_options,
            format_func=selected_document_label,
            key="document_selection",
            help=(
                "Select one document for focused answers, "
                "or All documents to search across your uploads."
            ),
        )

        st.caption("Uploaded in this session")

        for document in documents:
            st.markdown(f"**{document['filename']}**")
            st.caption(
                f"{document['chunks']} chunks indexed · "
                f"ID {document['document_id'][:6]}"
            )

    else:
        st.info(
            "Upload a PDF or TXT document to enable "
            "document selection."
        )

    st.divider()
    st.markdown("## 💬 Chats")

    if st.button(
        "＋ New Chat",
        use_container_width=True,
        key="new_chat_button",
    ):
        create_new_chat()
        st.rerun()

    chat_ids = list(st.session_state.chat_sessions.keys())

    if st.session_state.chat_selector not in chat_ids:
        st.session_state.chat_selector = (
            st.session_state.active_chat_id
        )

    st.selectbox(
        "Your conversations",
        options=chat_ids,
        format_func=lambda chat_id: (
            st.session_state.chat_sessions[chat_id]["title"]
        ),
        key="chat_selector",
        on_change=switch_chat,
    )

    active_chat_id = st.session_state.active_chat_id
    active_chat = st.session_state.chat_sessions[active_chat_id]

    with st.expander("Manage current chat"):
        st.text_input(
            "Chat name",
            key="rename_input",
            max_chars=60,
        )

        if st.button(
            "Rename chat",
            use_container_width=True,
            key="rename_chat_button",
        ):
            new_title = st.session_state.rename_input.strip()

            if new_title:
                active_chat["title"] = new_title
                st.success("Chat renamed.")
                st.rerun()
            else:
                st.warning("Enter a chat name first.")

        if st.button(
            "Clear messages",
            use_container_width=True,
            key="clear_chat_button",
        ):
            active_chat["messages"] = []
            st.session_state.confirm_delete = False
            st.rerun()

        if st.button(
            "Delete chat",
            use_container_width=True,
            key="delete_chat_button",
        ):
            st.session_state.confirm_delete = True
            st.rerun()

        if st.session_state.confirm_delete:
            st.warning(
                "Delete this chat and its message history?"
            )

            confirm_col, cancel_col = st.columns(2)

            with confirm_col:
                st.button(
                    "Confirm delete",
                    use_container_width=True,
                    key="confirm_delete_button",
                    on_click=confirm_delete_current_chat,
                )

            with cancel_col:
                st.button(
                    "Cancel",
                    use_container_width=True,
                    key="cancel_delete_button",
                    on_click=cancel_delete_current_chat,
                )

    st.caption(
        "Built with Streamlit, FastAPI, ChromaDB and Groq."
    )


# -------------------- Main chat area --------------------

st.markdown(
    """
    <div class="hero">
        <h1>🤖 Genaibot</h1>
        <p>
            Your AI document assistant. Upload a document, ask a
            question, and explore its contents through conversational AI.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("### Document conversation")

active_chat_id = st.session_state.active_chat_id
active_chat = st.session_state.chat_sessions[active_chat_id]
messages = active_chat["messages"]

if not messages:
    st.subheader("What would you like to know?")

    st.write(
        "Choose a document in the sidebar, then ask a question "
        "about its contents."
    )

    suggestions = [
        "Summarize the document",
        "What are the key points?",
        "Explain the main concepts",
    ]

    columns = st.columns(len(suggestions))

    for index, (column, suggestion) in enumerate(
        zip(columns, suggestions)
    ):
        with column:
            if st.button(
                suggestion,
                use_container_width=True,
                key=f"suggestion_{active_chat_id}_{index}",
            ):
                st.session_state.pending_question = suggestion
                st.rerun()


# -------------------- Conversation history --------------------

for message in messages:
    with st.chat_message(message.get("role", "assistant")):
        st.markdown(message.get("content", ""))
        display_citations(message)


# -------------------- Chat input --------------------

pending_question = st.session_state.pending_question

question = st.chat_input(
    "Ask a question about your documents...",
    key="chat_input",
)

if pending_question:
    question = pending_question
    st.session_state.pending_question = None


# -------------------- Question handling --------------------

if question:
    active_chat_id = st.session_state.active_chat_id
    active_chat = st.session_state.chat_sessions[active_chat_id]
    messages = active_chat["messages"]

    messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    if (
        len(messages) == 1
        and active_chat["title"] == "New Chat"
    ):
        active_chat["title"] = question[:40] or "New Chat"

    with st.chat_message("user"):
        st.markdown(question)

    selected_option = st.session_state.get(
        "document_selection",
        "__none__",
    )

    selected_document_id = (
        selected_option
        if selected_option not in ("__none__", "__all__")
        else None
    )

    search_all_documents = selected_option == "__all__"

    with st.chat_message("assistant"):
        if not selected_document_id and not search_all_documents:
            answer = (
                "Please upload a PDF or TXT document and select it "
                "under 'Answer using' before asking questions."
            )

            st.info(answer)

            messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                    "sources": [],
                    "citations": [],
                }
            )

        else:
            try:
                with st.spinner(
                    "Searching your documents and generating an answer..."
                ):
                    chat_payload = {
                        "question": question,
                        "top_k": 4,
                    }

                    if selected_document_id:
                        chat_payload["document_id"] = (
                            selected_document_id
                        )

                    response = httpx.post(
                        f"{API_URL}/chat",
                        json=chat_payload,
                        timeout=190.0,
                    )

                if response.is_success:
                    result = response.json()

                    answer = result.get("answer", "")

                    assistant_message = {
                        "role": "assistant",
                        "content": answer,
                        "sources": result.get("sources", []),
                        "citations": result.get("citations", []),
                    }

                    st.markdown(answer)
                    display_citations(assistant_message)
                    messages.append(assistant_message)

                else:
                    error_message = (
                        f"The API returned an error "
                        f"({response.status_code}). Please try again."
                    )

                    st.error(error_message)
                    st.caption(response.text[:400])

                    messages.append(
                        {
                            "role": "assistant",
                            "content": error_message,
                            "sources": [],
                            "citations": [],
                        }
                    )

            except httpx.RequestError as exc:
                error_message = (
                    "I couldn't connect to Genaibot's backend. "
                    "Please check the API URL and try again."
                )

                st.error(error_message)
                st.caption(str(exc)[:300])

                messages.append(
                    {
                        "role": "assistant",
                        "content": error_message,
                        "sources": [],
                        "citations": [],
                    }
                )
