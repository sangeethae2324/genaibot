
from pathlib import Path
from pypdf import PdfReader


def load_document(file_path: str) -> str:
    """Extract text from a PDF or TXT document."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    extension = path.suffix.lower()

    if extension == ".pdf":
        reader = PdfReader(str(path))
        text = "\n".join(
            page.extract_text() or "" for page in reader.pages
        )
    elif extension == ".txt":
        text = path.read_text(encoding="utf-8-sig")
    else:
        raise ValueError("Only PDF and TXT files are supported.")

    text = "\n".join(line.strip() for line in text.splitlines())
    return text.strip()


def split_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[str]:
    """Split text into overlapping character-based chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between 0 and chunk_size.")

    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks


def process_document(file_path: str) -> list[str]:
    """Load a document and return its text chunks."""
    text = load_document(file_path)
    return split_text(text)
