#!/usr/bin/env python
"""
Extract detailed explanations from a DOCX exam file and output a JSON
list of {id, explanation} objects that can be merged into the
open_book_explanations.json pipeline.

Assumptions (which match your exams):

- Block 1: Questions (Q1–Q40)
- Block 2: Answers (A1–A40) with detailed explanations.
- Answer lines start with a number and a letter, e.g.:
    "1. B. Parking ratio --- rehabilitation clinic."
  followed by one or more lines of explanation text.

ID pattern in the JSON question bank:

    data/<DOCX_FILENAME>::Q<number>

Example:

    data/Exam-OB-20251005-40Q-SPINAL-CLINIC-11B-DETAIL-SET-UID-9L7QK8.docx::Q1

USAGE (from project root):

    cd "C:\\Users\\Jas\\Documents\\CASp Generator\\Open Book\\casp_generator\\casp-rag"
    python extract_explanations_from_docx.py \
        "data\\Exam-OB-20251005-40Q-SPINAL-CLINIC-11B-DETAIL-SET-UID-9L7QK8.docx" \
        "spinal_clinic_explanations.json"

Then manually merge spinal_clinic_explanations.json into your global
open_book_explanations.json (or adjust merge_explanations.py to read it).
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import docx  # python-docx
except ImportError:
    raise SystemExit(
        "python-docx is not installed.\n"
        "Install it with:\n"
        "  python -m pip install python-docx"
    )

PROJECT_ROOT = Path(__file__).resolve().parent


def load_docx_paragraphs(docx_path: Path) -> List[str]:
    """Load all paragraph texts from a DOCX file."""
    document = docx.Document(str(docx_path))
    lines: List[str] = []
    for para in document.paragraphs:
        text = para.text.strip()
        if text:
            lines.append(text)
    return lines


def split_blocks(lines: List[str]) -> Tuple[List[str], List[str]]:
    """
    Split the DOCX text into two blocks:
    - Block 1: Questions (from start until "Block 2" line)
    - Block 2: Everything after "Block 2"
    """
    block1: List[str] = []
    block2: List[str] = []
    in_block2 = False

    for line in lines:
        # Look for a line that clearly marks Block 2 Answers.
        # Your document uses: "**Block 2 -- Answers (A1--A40)**"
        normalized = line.lower().replace(" ", "")
        if "block2" in normalized and "answers" in normalized:
            in_block2 = True
            continue

        if in_block2:
            block2.append(line)
        else:
            block1.append(line)

    return block1, block2


ANSWER_HEADER_RE = re.compile(
    r"^\s*(\d+)\s*[\.\)]\s*([A-Da-d])[\.\)]?\s*(.*)$"
)


def parse_block2_answers(block2_lines: List[str]) -> Dict[int, str]:
    """
    Parse Block 2 lines into:
        { question_number: full_explanation_text }

    - A header line looks like: "1. B. Title..." or "1. B) Title..."
    - All following lines until the next header belong to that question's explanation.
    """
    explanations: Dict[int, List[str]] = {}
    current_qnum: int = None

    for line in block2_lines:
        m = ANSWER_HEADER_RE.match(line)
        if m:
            # Start of a new answer
            qnum_str, correct_letter, rest = m.groups()
            qnum = int(qnum_str)
            current_qnum = qnum
            # Start explanation with header line minus the leading "1. B."
            header_text = rest.strip()
            explanations[current_qnum] = []
            if header_text:
                explanations[current_qnum].append(header_text)
        else:
            # Continuation of current explanation
            if current_qnum is not None:
                explanations[current_qnum].append(line.strip())

    # Join explanation lines into single strings
    joined: Dict[int, str] = {}
    for qnum, parts in explanations.items():
        # Filter out any accidental empty lines
        cleaned = [p for p in parts if p]
        joined[qnum] = " ".join(cleaned)
    return joined


def build_id_for_question(docx_path: Path, qnum: int) -> str:
    """
    Build the JSON question ID string for this DOCX and question number,
    matching your question bank convention.
    """
    # In your JSON: id is "data/<DOCX_FILENAME>::Q<number>"
    # DOCX lives under "data\\...". We'll just use that pattern.
    return f"data/{docx_path.name}::Q{qnum}"


def build_explanation_objects(
    docx_path: Path,
    explanations_by_qnum: Dict[int, str],
) -> List[Dict[str, str]]:
    """
    Turn {qnum: explanation_text} into a list of:
        {"id": "...::Qn", "explanation": "..."}
    """
    items: List[Dict[str, str]] = []

    for qnum in sorted(explanations_by_qnum.keys()):
        explanation_text = explanations_by_qnum[qnum].strip()
        if not explanation_text:
            continue
        qid = build_id_for_question(docx_path, qnum)
        items.append(
            {
                "id": qid,
                "explanation": explanation_text,
            }
        )
    return items


def save_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    import sys

    if len(sys.argv) != 3:
        print(
            "Usage:\n"
            "  python extract_explanations_from_docx.py "
            "\"data\\Exam-OB-20251005-40Q-SPINAL-CLINIC-11B-DETAIL-SET-UID-9L7QK8.docx\" "
            "\"spinal_clinic_explanations.json\""
        )
        sys.exit(1)

    docx_relative = sys.argv[1]
    output_json_name = sys.argv[2]

    docx_path = PROJECT_ROOT / docx_relative
    output_json_path = PROJECT_ROOT / output_json_name

    print(f"Reading DOCX from: {docx_path}")
    lines = load_docx_paragraphs(docx_path)

    print(f"Loaded {len(lines)} non-empty lines from DOCX.")
    block1, block2 = split_blocks(lines)
    print(f"Block 1 lines: {len(block1)}")
    print(f"Block 2 lines: {len(block2)}")

    explanations_by_qnum = parse_block2_answers(block2)
    print(f"Parsed explanations for {len(explanations_by_qnum)} questions.")

    explanation_objects = build_explanation_objects(docx_path, explanations_by_qnum)
    print(f"Built {len(explanation_objects)} explanation objects with IDs.")

    save_json(output_json_path, explanation_objects)
    print(f"Wrote explanations JSON to: {output_json_path}")


if __name__ == "__main__":
    main()
