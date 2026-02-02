# build_open_book_bank.py
"""
First-pass script to walk the data/ folder and collect raw text from
.docx and .pdf exam/reference files into a JSON file.

Next step (after you inspect the output):
- Add parsing rules that turn this raw text into fully structured
  questions (stem, choices A–D, correct answer, difficulty, etc.).
"""

import os
import json
from pathlib import Path

from docx import Document  # python-docx
from PyPDF2 import PdfReader  # pypdf


# Root folder for your project (this script assumes it is run from casp-rag)
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_JSON = PROJECT_ROOT / "open_book_questions_raw.json"


def is_interesting_file(path: Path) -> bool:
    """
    Decide which files to scan.
    For now: all .docx and .pdf under data/.
    You can tighten this later (e.g., only open-book exam files).
    """
    if not path.is_file():
        return False
    return path.suffix.lower() in {".docx", ".pdf"}


def extract_text_from_docx(path: Path) -> str:
    """
    Extract plain text from a .docx file using python-docx.
    """
    doc = Document(str(path))
    parts = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def extract_text_from_pdf(path: Path) -> str:
    """
    Extract plain text from a .pdf file using PyPDF2.
    This is a simple approach and may need tuning per document.
    """
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        text = (page.extract_text() or "").strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def build_raw_bank() -> None:
    """
    Walk data/, read interesting files, and write raw text blocks into JSON.
    """
    raw_entries = []

    if not DATA_DIR.exists():
        print(f"data/ folder not found at: {DATA_DIR}")
        return

    print(f"Scanning data folder: {DATA_DIR}")

    for root, dirs, files in os.walk(DATA_DIR):
        root_path = Path(root)
        for name in files:
            file_path = root_path / name
            if not is_interesting_file(file_path):
                continue

            print(f"Reading: {file_path}")
            try:
                if file_path.suffix.lower() == ".docx":
                    text = extract_text_from_docx(file_path)
                elif file_path.suffix.lower() == ".pdf":
                    text = extract_text_from_pdf(file_path)
                else:
                    continue
            except Exception as e:
                print(f"  Error reading {file_path}: {e}")
                continue

            if not text:
                print(f"  No text found in {file_path}, skipping.")
                continue

            raw_entries.append(
                {
                    "source_path": str(file_path.relative_to(PROJECT_ROOT)),
                    "exam_type_guess": "open_or_closed_unknown",
                    "raw_text": text,
                }
            )

    print(f"\nCollected {len(raw_entries)} raw text entries.")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(raw_entries, f, ensure_ascii=False, indent=2)

    print(f"Raw open-book question bank written to: {OUTPUT_JSON}")


if __name__ == "__main__":
    build_raw_bank()
