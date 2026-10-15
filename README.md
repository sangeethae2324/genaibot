# Genaibot - AI-Powered RAG Chatbot

Genaibot is a Retrieval-Augmented Generation (RAG) chatbot that answers questions using information from uploaded documents. It retrieves relevant document chunks and uses a local large language model to generate context-aware answers.

## Features

- Upload PDF and TXT documents.
- Extract and split document text into chunks.
- Generate embeddings using Sentence Transformers.
- Store and retrieve document chunks using ChromaDB.
- Generate answers using the Llama 3.2 model through Ollama.
- Display source documents alongside answers.
- Provide a web interface using Streamlit.
- Expose REST API endpoints using FastAPI.

## Technology Stack

- **Language:** Python
- **Frontend:** Streamlit
- **Backend:** FastAPI
- **Vector Database:** ChromaDB
- **Embeddings:** Sentence Transformers
- **LLM Runtime:** Ollama
- **Language Model:** Llama 3.2
- **Document Processing:** pypdf
- **HTTP Client:** HTTPX

## Project Structure

```text
genaichatbot/
+-- app/
¦   +-- __init__.py
¦   +-- config.py
¦   +-- ingestion.py
¦   +-- vector_store.py
¦   +-- rag.py
¦   +-- main.py
¦   +-- ui.py
+-- data/
+-- tests/
+-- .env
+-- .gitignore
+-- requirements.txt
```

## Prerequisites

- Python 3.13
- Ollama
- Git (for version control)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/genaibot.git
cd genaibot
```

Replace `YOUR_USERNAME` with your GitHub username.

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

### 3. Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. Install and start Ollama

Install Ollama from https://ollama.com/download.

Download the model:

```powershell
ollama pull llama3.2
```

If the `ollama` command is not recognized, open Ollama from the Start menu or use its installed executable.

## Running the Application

Keep the Ollama service running.

### Start the FastAPI backend

Open a terminal in the project directory and run:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Backend URL: http://127.0.0.1:8000

API documentation: http://127.0.0.1:8000/docs

### Start the Streamlit frontend

Open another terminal in the project directory and run:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/ui.py
```

Frontend URL: http://localhost:8501

## How It Works

1. Upload a PDF or TXT document.
2. Extract its text and divide it into overlapping chunks.
3. Convert the chunks into vector embeddings.
4. Store the embeddings and metadata in ChromaDB.
5. Convert a user question into an embedding.
6. Retrieve relevant document chunks.
7. Send the retrieved context and question to Llama 3.2.
8. Display the generated answer and source information.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Basic API information |
| GET | `/health` | Health check |
| POST | `/upload` | Upload and index a document |
| POST | `/chat` | Ask a question |

## Current Limitations

- Supports PDF and TXT documents.
- Requires a running Ollama service and a downloaded model.
- Answers depend on the quality and content of uploaded documents.
- Local document storage and the vector database are not included in the Git repository.
- Cloud deployment requires a cloud-accessible inference setup or a hosted model API.

## Future Improvements

- Add automated tests and CI.
- Support additional document formats.
- Improve retrieval quality and document management.
- Add authentication and upload limits.
- Deploy the frontend and backend.
- Add evaluation metrics for retrieval and answer quality.

## Security

Never commit API keys, passwords, private documents, local databases, or environment files containing secrets. Review `.gitignore` before publishing the repository.

## License

Choose an appropriate open-source license before distributing this project.
