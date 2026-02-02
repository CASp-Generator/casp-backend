from typing import List, Dict, Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


CHROMA_DB_DIR = "./casp_chroma"
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

COLLECTIONS = [
    "casp_concepts_textbook",
    "casp_exams_open_book",
    "casp_exams_closed_book",
    "casp_reference_tools",
]


def _get_client_and_model():
    client = chromadb.PersistentClient(
        path=CHROMA_DB_DIR,
        settings=Settings(anonymized_telemetry=False),
    )
    embed_model = SentenceTransformer(EMBED_MODEL_NAME)
    return client, embed_model


def get_rag_snippets(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Return top-k relevant chunks across all CASp collections as data.

    Each result dict has:
      - collection: str
      - id: str
      - doc: str          (text chunk)
      - meta: Dict[str, Any]  (source_id, exam_theme, difficulty, jurisdiction_tags)
      - dist: float       (vector distance; lower is closer)
    """
    client, embed_model = _get_client_and_model()

    vec = embed_model.encode([query]).tolist()[0]

    results_all: List[Dict[str, Any]] = []

    for name in COLLECTIONS:
        col = client.get_collection(name)
        res = col.query(
            query_embeddings=[vec],
            n_results=k,
        )

        for i in range(len(res["ids"][0])):
            results_all.append(
                {
                    "collection": name,
                    "id": res["ids"][0][i],
                    "doc": res["documents"][0][i],
                    "meta": res["metadatas"][0][i],
                    "dist": res["distances"][0][i],
                }
            )

    results_all.sort(key=lambda x: x["dist"])

    return results_all[:k]
