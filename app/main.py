
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.ingestion import process_document
from app.rag import ask_question
from app.vector_store import index_chunks


app = FastAPI(
    title="Genaibot API",
    description="A document-grounded Generative AI chatbot.",
    version="0.1.0",
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"
DATA_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".pdf", ".txt"}


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=4, ge=1, le=10)


@app.get("/")
def home():
    return {
        "message": "Welcome to Genaibot!",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported.",
        )

    document_id = uuid4().hex
    destination = DATA_DIR / f"{document_id}{extension}"

    try:
        content = await file.read(MAX_FILE_SIZE + 1)

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="File exceeds the 10 MB limit.",
            )

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        destination.write_bytes(content)

        chunks = process_document(str(destination))

        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="No extractable text found in the document.",
            )

        indexed_count = index_chunks(
            chunks=chunks,
            source=filename,
            document_id=document_id,
        )

        return {
            "message": "Document uploaded and indexed successfully.",
            "filename": filename,
            "document_id": document_id,
            "chunks_indexed": indexed_count,
        }

    except HTTPException:
        destination.unlink(missing_ok=True)
        raise

    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(exc)[:300]}",
        ) from exc

    finally:
        await file.close()


@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        return await ask_question(
            question=request.question,
            top_k=request.top_k,
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
