from casp_rag_client import get_rag_snippets


def main() -> None:
    # Change this query string to anything you want to test
    query = "CBC 11B parking access aisle"
    get_rag_snippets(query, k=3)


if __name__ == "__main__":
    main()
