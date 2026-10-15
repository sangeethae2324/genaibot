
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_DIR = DATA_DIR / "chroma_db"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# A lightweight multilingual embedding model.
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_embedding_model = None
_client = None
_collection = None


def get_embedding_model():
    """Load the embedding model only when needed."""
    global _embedding_model

    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    return _embedding_model


def get_collection():
    """Return the persistent ChromaDB collection."""
    global _client, _collection

    if _collection is None:
        _client = chromadb.PersistentClient(path=str(DB_DIR))
        _collection = _client.get_or_create_collection(
            name="genaibot_documents",
            metadata={"hnsw:space": "cosine"},
        )

    return _collection


def index_chunks(
    chunks: list[str],
    source: str,
    document_id: str,
) -> int:
    """Embed and store document chunks in ChromaDB."""
    if not chunks:
        return 0

    model = get_embedding_model()
    collection = get_collection()

    embeddings = model.encode(
        chunks,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()

    ids = [f"{document_id}_{i}" for i in range(len(chunks))]

    metadatas = [
        {
            "source": source,
            "document_id": document_id,
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]

    # Upsert allows the same chunk IDs to be updated.
    collection.upsert(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return len(chunks)


def search_chunks(query: str, top_k: int = 4) -> list[dict]:
    """Retrieve the most relevant chunks for a question."""
    if not query.strip():
        return []

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    collection = get_collection()

    if collection.count() == 0:
        return []

    model = get_embedding_model()
    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    valid_results = []

    for document, metadata, distance in zip(
        documents, metadatas, distances
    ):
        if not document or not isinstance(metadata, dict):
            continue

        source = metadata.get("source")
        document_id = metadata.get("document_id")

        if not source or not document_id:
            continue

        valid_results.append(
            {
                "text": document,
                "source": source,
                "document_id": document_id,
                "chunk_index": metadata.get("chunk_index", -1),
                "distance": distance,
            }
        )

        if len(valid_results) >= top_k:
            break

    return valid_results

