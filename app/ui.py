
import os

import httpx
import streamlit as st

API_URL = st.secrets.get(
    "API_URL",
    os.getenv("API_URL", "http://127.0.0.1:8000")
)
st.set_page_config(
    page_title="Genaibot",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Genaibot")
st.caption("Your AI assistant for answering questions from documents.")

# Initialize chat history.
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar: document upload.
with st.sidebar:
    st.header("📄 Knowledge Base")
    st.write("Upload a PDF or TXT document to chat with its contents.")

    uploaded_file = st.file_uploader(
        "Choose a document",
        type=["pdf", "txt"],
    )

    if st.button(
        "Upload and index",
        disabled=uploaded_file is None,
        use_container_width=True,
    ):
        try:
            with st.spinner("Processing and indexing document..."):
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
                st.success(result["message"])
                st.write(f"**File:** {result['filename']}")
                st.write(
                    f"**Chunks indexed:** {result['chunks_indexed']}"
                )
            else:
                st.error(f"Upload failed: {response.text[:500]}")

        except httpx.RequestError:
            st.error(
                "Cannot connect to Genaibot's API. "
                "Make sure the FastAPI server is running."
            )

    st.divider()

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.caption("Powered by FastAPI, ChromaDB and Ollama.")

# Display existing conversation.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message.get("sources"):
            with st.expander("View sources"):
                for source in message["sources"]:
                    st.write(f"📄 {source}")

# Chat input.
question = st.chat_input("Ask a question about your documents...")

if question:
    st.session_state.messages.append(
        {"role": "user", "content": question}
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Genaibot is thinking..."):
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
                    with st.expander("View sources"):
                        for source in sources:
                            st.write(f"📄 {source}")

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                    }
                )

            else:
                error_message = (
                    f"API error ({response.status_code}): "
                    f"{response.text[:500]}"
                )
                st.error(error_message)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error_message,
                    }
                )

        except httpx.RequestError:
            error_message = (
                "I couldn't connect to Genaibot's backend. "
                "Check that the FastAPI server is running."
            )
            st.error(error_message)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_message,
                }
            )
