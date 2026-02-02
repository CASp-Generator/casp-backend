# casp_tools/generate_open_book_from_rag.py

import os
import sys

# Find casp-rag folder (sibling of casp_tools)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)  # casp_generator
CASP_RAG_DIR = os.path.join(PROJECT_ROOT, "casp-rag")

if CASP_RAG_DIR not in sys.path:
    sys.path.insert(0, CASP_RAG_DIR)

# Import the run_generation helper from the casp-rag script
from generate_open_book_from_rag import run_generation  # type: ignore


def main():
    """
    Generate questions for ALL difficulties in one go.
    """
    for difficulty in ["easy", "medium", "hard", "test_prep"]:
        run_generation(difficulty=difficulty)


if __name__ == "__main__":
    main()
