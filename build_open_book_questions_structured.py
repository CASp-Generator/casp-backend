# build_open_book_questions_structured.py
"""
Parse open_book_questions_raw.json into a structured open_book_questions.json
containing real multiple-choice questions for the CASp open-book engine.

This script assumes patterns like:

Q1. Question text...
A. Option A text...
B. Option B text...
C. Option C text...
D. Option D text...

from exam-style docs such as:
"Exam – OB-20250919-60Q-SPINAL-CLINIC-11B (Corrected Version 4).docx"
"""

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
RAW_JSON_PATH = PROJECT_ROOT / "open_book_questions_raw.json"
OUTPUT_JSON_PATH = PROJECT_ROOT / "open_book_questions.json"


def load_raw_entries():
    if not RAW_JSON_PATH.exists():
        raise FileNotFoundError(f"Raw JSON not found at: {RAW_JSON_PATH}")
    with open(RAW_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def is_exam_source(source_path: str) -> bool:
    """
    Decide which raw entries are actual exam question sets.
    Start narrow with obvious exam naming; you can expand this later.
    """
    lowered = source_path.lower()
    # Obvious exam-style patterns (you can add more keywords)
    exam_keywords = [
        "exam – ob-",   # your spinal clinic exam sample
        "exam - ob-",   # safety for plain hyphen
        "practice test",
        "simulation exam",
        "questions (1–60)",
        "questions (1-60)",
        "open-book exam",
        "ob-2025",      # your OB-20... codes
    ]
    return any(k in lowered for k in exam_keywords)


def parse_exam_text_to_questions(raw_text: str, source_path: str):
    """
    Parse the raw_text from a single exam file into a list of question dicts.

    Pattern expected:
    Q1. Question text...
    A. Choice text...
    B. Choice text...
    C. Choice text...
    D. Choice text...
    Q2. ...

    Correct answers and difficulty are not encoded in this text yet, so:
    - correct_choice will be set to None for now.
    - difficulty will be set to "medium" as a placeholder.
    """
    questions = []

    # Split into lines and strip trailing whitespace
    lines = [line.rstrip() for line in raw_text.splitlines()]

    # Regex for question start: e.g., Q1., Q10., etc.
    q_pattern = re.compile(r"^Q(\d+)\.\s*(.*)$")
    # Regex for answer choices: A., B., C., D. at start of line
    a_pattern = re.compile(r"^A\.\s*(.*)$")
    b_pattern = re.compile(r"^B\.\s*(.*)$")
    c_pattern = re.compile(r"^C\.\s*(.*)$")
    d_pattern = re.compile(r"^D\.\s*(.*)$")

    current_q = None  # holds a dict while we fill it
    current_choices = {}

    def flush_current():
        nonlocal current_q, current_choices
        if current_q is not None and len(current_choices) == 4:
            q_number = current_q["number"]
            text = current_q["text"]
            # Build a stable ID from source + Q-number
            base_id = f"{source_path}::Q{q_number}"
            q_id = base_id.replace("\\", "/")
            questions.append(
                {
                    "id": q_id,
                    "text": text,
                    "choices": current_choices.copy(),
                    "correct_choice": None,  # will be filled later
                    "difficulty": "medium",  # placeholder
                    "exam_type": "open",
                    "category": None,
                    "explanation": "",
                    "source_path": source_path,
                    "q_number": q_number,
                }
            )
        # Reset
        current_q = None
        current_choices = {}

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for question line
        m_q = q_pattern.match(line)
        if m_q:
            # Flush previous question if it has full choices
            flush_current()
            q_number = int(m_q.group(1))
            q_text = m_q.group(2).strip()
            current_q = {"number": q_number, "text": q_text}
            current_choices = {}
            continue

        if current_q is None:
            # Not inside a question yet; skip
            continue

        # Choices
        m_a = a_pattern.match(line)
        if m_a:
            current_choices["A"] = m_a.group(1).strip()
            continue

        m_b = b_pattern.match(line)
        if m_b:
            current_choices["B"] = m_b.group(1).strip()
            continue

        m_c = c_pattern.match(line)
        if m_c:
            current_choices["C"] = m_c.group(1).strip()
            continue

        m_d = d_pattern.match(line)
        if m_d:
            current_choices["D"] = m_d.group(1).strip()
            continue

        # If the line does not match Q or A–D but we have a current question,
        # append it to the question text (for multi-line stems)
        if current_q is not None and not any(current_choices.get(k) for k in ["A", "B", "C", "D"]):
            # Still in the question stem section, before choices start
            current_q["text"] += " " + line

    # Flush at the end
    flush_current()

    return questions


def build_structured_questions():
    raw_entries = load_raw_entries()
    structured_questions = []

    for entry in raw_entries:
        source_path = entry.get("source_path", "")
        raw_text = entry.get("raw_text", "")

        if not source_path or not raw_text:
            continue

        if not is_exam_source(source_path):
            # Skip non-exam docs for now (CBC text, guides, etc.)
            continue

        print(f"Parsing exam-style file: {source_path}")
        qs = parse_exam_text_to_questions(raw_text, source_path)
        print(f"  Found {len(qs)} questions.")
        structured_questions.extend(qs)

    print(f"\nTotal structured questions parsed: {len(structured_questions)}")

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(structured_questions, f, ensure_ascii=False, indent=2)

    print(f"Structured open-book questions written to: {OUTPUT_JSON_PATH}")


if __name__ == "__main__":
    build_structured_questions()
