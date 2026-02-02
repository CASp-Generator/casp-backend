import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

CHROMA_DB_DIR = "./casp_chroma"
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

def run_query(query: str, k: int = 5):
    embed_model = SentenceTransformer(EMBED_MODEL_NAME)
    client = chromadb.PersistentClient(
        path=CHROMA_DB_DIR,
        settings=Settings(anonymized_telemetry=False)
    )

    collections = [
        "casp_concepts_textbook",
        "casp_exams_open_book",
        "casp_exams_closed_book",
        "casp_reference_tools",
    ]

    vec = embed_model.encode([query]).tolist()[0]
    results_all = []

    for name in collections:
        col = client.get_collection(name)
        res = col.query(
            query_embeddings=[vec],
            n_results=k
        )
        for i in range(len(res["ids"][0])):
            results_all.append({
                "collection": name,
                "id": res["ids"][0][i],
                "doc": res["documents"][0][i],
                "meta": res["metadatas"][0][i],
                "dist": res["distances"][0][i],
            })

    results_all.sort(key=lambda x: x["dist"])

    print(f"\nTop {k} results for: {query!r}\n")
    for r in results_all[:k]:
        print("-" * 80)
        print("Collection:", r["collection"])
        print("Source:", r["meta"]["source_id"])
        print("Theme:", r["meta"]["exam_theme"], "| Difficulty:", r["meta"]["difficulty"])
        print("Jurisdictions:", r["meta"]["jurisdiction_tags"])
        print("\nSnippet:\n", r["doc"][:600], "...")
        print("-" * 80)


if __name__ == "__main__":
    run_query("CBC 11B requirements for spinal care clinic parking")
