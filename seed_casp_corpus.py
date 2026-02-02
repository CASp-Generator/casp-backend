import os
import uuid
from pathlib import Path
from typing import List, Dict, Tuple

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from docx import Document as DocxDocument
from pypdf import PdfReader

# --------- CONFIG ---------
DATA_DIR = "./data"
CHROMA_DB_DIR = "./casp_chroma"
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Chunking
MAX_CHARS_PER_CHUNK = 1200  # ~400–600 tokens

# Collections
COLLECTION_CONCEPTS = "casp_concepts_textbook"
COLLECTION_OPEN_BOOK = "casp_exams_open_book"
COLLECTION_CLOSED_BOOK = "casp_exams_closed_book"
COLLECTION_TOOLS = "casp_reference_tools"


# --------- UTILS ---------
def read_docx(path: Path) -> str:
    doc = DocxDocument(str(path))
    parts = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        text = (page.extract_text() or "").strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def read_txt(path: Path) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def load_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return read_docx(path)
    if suffix == ".pdf":
        return read_pdf(path)
    if suffix in [".txt", ".md"]:
        return read_txt(path)
    # skip unknown
    return ""


def chunk_text(text: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> List[str]:
    text = text.replace("\r\n", "\n")
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for para in paragraphs:
        if len(para) > max_chars:
            # hard split very long paragraphs
            start = 0
            while start < len(para):
                end = start + max_chars
                chunks.append(para[start:end])
                start = end
            continue

        if current_len + len(para) + 2 <= max_chars:
            current.append(para)
            current_len += len(para) + 2
        else:
            if current:
                chunks.append("\n\n".join(current))
            current = [para]
            current_len = len(para)

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def classify_file(path: Path) -> Tuple[str, str, str, str]:
    """
    Returns:
      collection_name, exam_theme, difficulty, jurisdiction
    """
    name = path.name.lower()

    # Very rough heuristics; adjust as needed
    if "review-guide" in name or "review_guide" in name or "quiz-master" in name:
        return COLLECTION_CONCEPTS, "CASp Textbook / Concepts", "medium", "CBC_11B"

    if "spinal" in name or "clinic" in name:
        return COLLECTION_OPEN_BOOK, "Spinal Care Clinic", "medium", "CBC_11B"

    if "closed-book" in name or "Closed-Book" in name or "closed_book" in name:
        return COLLECTION_CLOSED_BOOK, "Closed-Book Style", "hard", "CBC_11B"

    if "parking" in name or "evcs" in name or "scoping" in name or "cheat" in name:
        return COLLECTION_TOOLS, "Reference / Tools", "easy", "CBC_11B"

    # default fallbacks
    return COLLECTION_OPEN_BOOK, "General CASp", "medium", "CBC_11B"


# --------- MAIN SEED ---------
def main():
    print("Loading embedding model...")
    embed_model = SentenceTransformer(EMBED_MODEL_NAME)

    print("Initializing Chroma DB...")
    client = chromadb.PersistentClient(
        path=CHROMA_DB_DIR,
        settings=Settings(anonymized_telemetry=False),
    )

    # create collections (id type is string)
    collections = {
        COLLECTION_CONCEPTS: client.get_or_create_collection(
            COLLECTION_CONCEPTS, metadata={"hnsw:space": "cosine"}, embedding_function=None
        ),
        COLLECTION_OPEN_BOOK: client.get_or_create_collection(
            COLLECTION_OPEN_BOOK, metadata={"hnsw:space": "cosine"}, embedding_function=None
        ),
        COLLECTION_CLOSED_BOOK: client.get_or_create_collection(
            COLLECTION_CLOSED_BOOK, metadata={"hnsw:space": "cosine"}, embedding_function=None
        ),
        COLLECTION_TOOLS: client.get_or_create_collection(
            COLLECTION_TOOLS, metadata={"hnsw:space": "cosine"}, embedding_function=None
        ),
    }

    data_path = Path(DATA_DIR)
    all_files = sorted(
        [p for p in data_path.rglob("*") if p.is_file() and p.suffix.lower() in [".docx", ".pdf", ".txt", ".md"]],
        key=lambda p: p.name.lower(),
    )

    print(f"Found {len(all_files)} files in {DATA_DIR}")

    for path in all_files:
        collection_name, exam_theme, difficulty, jurisdiction = classify_file(path)
        collection = collections[collection_name]

        print(f"\nProcessing: {path.name}")
        print(f"  -> Collection: {collection_name}")

        text = load_text(path)
        if not text.strip():
            print("  -> Skipped (empty or unreadable)")
            continue

        chunks = chunk_text(text)
        print(f"  -> Chunks: {len(chunks)}")

        ids: List[str] = []
        docs: List[str] = []
        metas: List[Dict] = []

        base_id = path.stem

        for i, chunk in enumerate(chunks):
            chunk_id = f"{base_id}-{i}-{uuid.uuid4().hex[:8]}"
            ids.append(chunk_id)
            docs.append(chunk)
            metas.append(
                {
                    # ALL METADATA VALUES SIMPLE (NO LISTS)
                    "source_id": path.name,
                    "exam_theme": exam_theme,
                    "difficulty": difficulty,
                    "jurisdiction_tags": jurisdiction,  # e.g. "CBC_11B" (string, not list)
                }
            )

        # embed
        embeddings = embed_model.encode(docs, convert_to_numpy=True).tolist()

        collection.add(
            ids=ids,
            documents=docs,
            embeddings=embeddings,
            metadatas=metas,
        )

    print("\nSeeding complete.")
    print(f"Chroma DB stored at: {CHROMA_DB_DIR}")


if __name__ == "__main__":
    main()
