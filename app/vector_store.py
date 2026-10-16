from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_DIR = DATA_DIR / "chroma_db"

DATA_DIR.mkdir(parents=True, exist_ok=True)

_client = None
_collection = None


def get_collection():
    """Return the persistent ChromaDB collection."""
    global _client, _collection

    if _collection is None:
        _client = chromadb.PersistentClient(path=str(DB_DIR))
        _collection = _client.get_or_create_collection(
            name="genaibot_documents",
            metadata={"hnsw:space": "cosine"},
            embedding_function=DefaultEmbeddingFunction(),
        )

    return _collection


def index_chunks(
    chunks: list[str],
    source: str,
    document_id: str,
) -> int:
    """Embed and store document chunks using ChromaDB."""
    if not chunks:
        return 0

    collection = get_collection()

    ids = [f"{document_id}_{i}" for i in range(len(chunks))]

    metadatas = [
        {
            "source": source,
            "document_id": document_id,
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]

    collection.upsert(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
    )

    return len(chunks)


def search_chunks(
    query: str,
    top_k: int = 4,
    document_id: str | None = None,
) -> list[dict]:
    """Retrieve relevant chunks, optionally from one document."""
    if not query.strip():
        return []

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    collection = get_collection()
    total_chunks = collection.count()

    if total_chunks == 0:
        return []

    # Filter retrieval to the requested document when an ID is supplied.
    where_filter = (
        {"document_id": document_id}
        if document_id
        else None
    )

    if where_filter:
        matching = collection.get(
            where=where_filter,
            include=["metadatas"],
        )
        matching_count = len(matching.get("metadatas") or [])

        if matching_count == 0:
            return []

        result_count = min(top_k, matching_count)
    else:
        result_count = min(top_k, total_chunks)

    query_args = {
        "query_texts": [query],
        "n_results": result_count,
        "include": ["documents", "metadatas", "distances"],
    }

    if where_filter:
        query_args["where"] = where_filter

    results = collection.query(**query_args)

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
        stored_document_id = metadata.get("document_id")

        if not source or not stored_document_id:
            continue

        valid_results.append(
            {
                "text": document,
                "source": source,
                "document_id": stored_document_id,
                "chunk_index": metadata.get("chunk_index", -1),
                "distance": distance,
            }
        )

    return valid_results