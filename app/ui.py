
import os

import httpx
import streamlit as st

# Keep the existing backend configuration.

# Keep local development and Streamlit Cloud working.
try:
    API_URL = st.secrets["API_URL"]
except (KeyError, FileNotFoundError):
    API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

API_URL = API_URL.rstrip("/")


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
        margin-bottom: 1.5rem;
    }

    .hero h1 {
        color: white;
        margin-bottom: 0.35rem;
        font-size: 2.25rem;
    }

    .hero p {
        color: #e2e8f0;
        margin-bottom: 0;
        font-size: 1rem;
    }

    .section-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    div[data-testid="stChatMessage"] {
        border-radius: 14px;
        padding: 0.6rem;
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

# -------------------- Session state --------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_documents" not in st.session_state:
    st.session_state.uploaded_documents = []

# -------------------- Sidebar --------------------

with st.sidebar:
    st.markdown("## 📚 Knowledge Base")
    st.caption("Upload a document to start asking questions about its contents.")

    uploaded_file = st.file_uploader(
        "Choose a PDF or TXT file",
        type=["pdf", "txt"],
        help="Select a document you want Genaibot to read.",
    )

    if st.button(
        "Upload and index",
        disabled=uploaded_file is None,
        use_container_width=True,
        type="primary",
    ):
        try:
            with st.spinner("Reading and indexing your document..."):
                file_data = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        uploaded_file.type or "application/octet-stream",
                    )
                }

                response = httpx.post(
                    f"{API_URL}/upload",
                    files=file_data,
                    timeout=180.0,
                )

            if response.is_success:
                result = response.json()
                filename = result.get("filename", uploaded_file.name)
                chunks = result.get("chunks_indexed", 0)

                st.session_state.uploaded_documents.append(
                    {"filename": filename, "chunks": chunks}
                )

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
                "Couldn't reach the backend. Please try again in a moment."
            )
            st.caption(str(exc)[:250])

    if st.session_state.uploaded_documents:
        st.divider()
        st.markdown("### 📄 Uploaded this session")

        for document in st.session_state.uploaded_documents:
            st.markdown(f"**{document['filename']}**")
            st.caption(f"{document['chunks']} chunks indexed")

    st.divider()

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.caption("Built with Streamlit, FastAPI, ChromaDB and Groq.")

# -------------------- Main header --------------------

st.markdown(
    """
    <div class="hero">
        <h1>🤖 Genaibot</h1>
        <p>Your AI document assistant. Upload a document, ask a question,
        and explore its contents through conversational AI.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<p class="section-label">Document conversation</p>',
    unsafe_allow_html=True,
)

if not st.session_state.messages:
    st.subheader("What would you like to know?")
    st.write(
        "Upload a PDF or TXT file in the sidebar, then ask a question "
        "about its content."
    )

    suggestions = [
        "Summarize the document",
        "What are the key points?",
        "Explain the main concepts",
    ]

    cols = st.columns(len(suggestions))

    for col, suggestion in zip(cols, suggestions):
        with col:
            if st.button(suggestion, use_container_width=True):
                st.session_state.pending_question = suggestion
                st.rerun()

# -------------------- Conversation history --------------------

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message.get("sources"):
            with st.expander("📚 View sources"):
                for source in message["sources"]:
                    st.markdown(f"- `{source}`")

# -------------------- Chat input --------------------

pending_question = st.session_state.pop("pending_question", None)
question = st.chat_input("Ask a question about your documents...")

if pending_question:
    question = pending_question

if question:
    st.session_state.messages.append(
        {"role": "user", "content": question}
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Searching your documents and generating an answer..."):
                response = httpx.post(
                    f"{API_URL}/chat",
                    json={"question": question, "top_k": 4},
                    timeout=190.0,
                )

            if response.is_success:
                result = response.json()
                answer = result["answer"]
                sources = result.get("sources", [])

                st.markdown(answer)

                if sources:
                    with st.expander("📚 View sources"):
                        for source in sources:
                            st.markdown(f"- `{source}`")
                else:
                    st.caption("No source documents were returned for this answer.")

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                    }
                )

            else:
                error_message = (
                    f"The API returned an error ({response.status_code}). "
                    "Please try again."
                )
                st.error(error_message)
                st.caption(response.text[:400])

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error_message,
                    }
                )

        except httpx.RequestError:
            error_message = (
                "I couldn't connect to Genaibot's backend. "
                "Please try again shortly."
            )
            st.error(error_message)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_message,
                }
            )
