
for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        display_citations(message)


# -------------------- Chat input --------------------

pending_question = st.session_state.pending_question
question = st.chat_input("Ask a question about your documents...")

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

    if len(messages) == 1 and active_chat["title"] == "New Chat":
        active_chat["title"] = question[:40]

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):

        # Block searches if no document was explicitly selected.
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
                        chat_payload["document_id"] = selected_document_id

                    response = httpx.post(
                        f"{API_URL}/chat",
                        json=chat_payload,
                        timeout=190.0,
                    )

                if response.is_success:
                    result = response.json()
                    answer = result.get("answer", "")
                    sources = result.get("sources", [])
                    citations = result.get("citations", [])

                    st.markdown(answer)

                    assistant_message = {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "citations": citations,
                    }

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
