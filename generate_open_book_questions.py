import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import random

# ---------------------------------------------------------------------
# Paths (for your RAG folder)
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent

AUTHORED_BANK_PATH = PROJECT_ROOT / "open_book_questions_tagged.json"
GENERATED_BANK_PATH = PROJECT_ROOT / "generated_open_book_questions.json"

GENERATED_TESTS_ROOT = PROJECT_ROOT / "generated_tests"
OPEN_BOOK_TESTS_DIR = GENERATED_TESTS_ROOT / "open_book"

# ---------------------------------------------------------------------
# CASp open-book category structure (from exam metrics)
# ---------------------------------------------------------------------
# These map the exam report buckets (F–J) to CBC 11B divisions/descriptions.

CASP_CATEGORY_DEFS = [
    {
        "code": "11B-5/8",
        "label": "Div 2–5/8 Site, Parking, EVCS (F)",
        "bucket": "F",
    },
    {
        "code": "11B-4",
        "label": "Div 2–4 Accessible Routes (G)",
        "bucket": "G",
    },
    {
        "code": "11B-6",
        "label": "Div 2–6 Plumbing Elements and Facilities (H)",
        "bucket": "H",
    },
    {
        "code": "11B-7",
        "label": "Div 2–7 Communication Elements (I)",
        "bucket": "I",
    },
    {
        "code": "11B-9",
        "label": "Div 2–9 Built-In Elements and Features (J)",
        "bucket": "J",
    },
]

VALID_CBC_CATEGORIES = {c["code"] for c in CASP_CATEGORY_DEFS}
VALID_DIFFICULTIES = {"easy", "medium", "hard", "test_prep"}

# Hard cap for open-book tests (official exam length)
OPEN_BOOK_MAX_QUESTIONS = 40


# ---------------------------------------------------------------------
# Utilities for loading / saving banks and tests
# ---------------------------------------------------------------------


def load_json_list(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        raise ValueError(f"Expected a JSON list in {path}, got {type(data)}")


def save_json_list(path: Path, data: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_directories() -> None:
    OPEN_BOOK_TESTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# ID generation and de-duplication
# ---------------------------------------------------------------------


def collect_existing_ids(
    authored: List[Dict[str, Any]],
    generated: List[Dict[str, Any]],
) -> set:
    ids = set()
    for q in authored:
        qid = str(q.get("id", "")).strip()
        if qid:
            ids.add(qid)
    for q in generated:
        qid = str(q.get("id", "")).strip()
        if qid:
            ids.add(qid)
    return ids


def next_generated_id(existing_ids: set, exam_type: str = "open_book") -> str:
    """
    Generate a new unique ID for a generated question.
    Example: gen-ob-000001, gen-ob-000002, ...
    """
    prefix = "gen-ob-" if exam_type == "open_book" else "gen-cb-"
    max_n = 0
    for qid in existing_ids:
        if qid.startswith(prefix):
            tail = qid[len(prefix):]
            if tail.isdigit():
                n = int(tail)
                if n > max_n:
                    max_n = n
    n = max_n + 1
    new_id = f"{prefix}{n:06d}"
    while new_id in existing_ids:
        n += 1
        new_id = f"{prefix}{n:06d}"
    return new_id


# ---------------------------------------------------------------------
# Filtering authored questions for reference
# ---------------------------------------------------------------------


def filter_authored_by_category_and_difficulty(
    authored: List[Dict[str, Any]],
    cbc_category: str,
    difficulty: str,
) -> List[Dict[str, Any]]:
    """
    Return authored questions that match the given CBC category and difficulty.
    Difficulty is normalized to your four buckets: easy, medium, hard, test_prep.
    """
    cbc_category = cbc_category.strip()
    difficulty = difficulty.strip().lower()

    def norm_diff(raw: str) -> str:
        if not raw:
            return "medium"
        v = raw.strip().lower()
        if v in VALID_DIFFICULTIES:
            return v
        if v in {"beginner"}:
            return "easy"
        if v in {"intermediate"}:
            return "medium"
        if v in {"advanced"}:
            return "hard"
        return "medium"

    results = []
    for q in authored:
        cat = (q.get("category") or q.get("cbc_category") or "").strip()
        diff_raw = q.get("difficulty") or q.get("difficulty_band") or ""
        d = norm_diff(str(diff_raw))
        if cat == cbc_category and d == difficulty:
            results.append(q)

    return results


# ---------------------------------------------------------------------
# Simple similarity check (to avoid blatant copying)
# ---------------------------------------------------------------------


def is_too_similar(stem: str, existing_stems: List[str]) -> bool:
    """
    Very simple similarity guard:
    - Lowercase
    - Check if the new stem is exactly equal or a long substring of any existing stem,
      or vice versa.
    """
    new = (stem or "").strip().lower()
    if not new:
        return False
    for s in existing_stems:
        old = (s or "").strip().lower()
        if not old:
            continue
        if new == old:
            return True
        if len(new) >= 40 and (new in old or old in new):
            return True
    return False


def collect_all_stems(*banks: List[Dict[str, Any]]) -> List[str]:
    stems: List[str] = []
    for bank in banks:
        for q in bank:
            t = q.get("text") or q.get("stem")
            if isinstance(t, str):
                stems.append(t)
    return stems


# ---------------------------------------------------------------------
# Category helpers
# ---------------------------------------------------------------------


def pick_random_casp_category() -> Dict[str, str]:
    """
    Pick one CASp open-book category definition at random.
    Returns a dict with keys: code, label, bucket.
    """
    return random.choice(CASP_CATEGORY_DEFS)


# ---------------------------------------------------------------------
# Placeholder for model call (you will wire your provider here)
# ---------------------------------------------------------------------


def call_model_to_generate_question(
    *,
    exam_type: str,
    difficulty: str,
    cbc_category_code: str,
    cbc_category_label: str,
    topic: str,
    reference_snippets: List[str],
    reference_questions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    THIS IS THE ONLY PLACE YOU WILL NEED TO CHANGE WHEN YOU WIRE AN ACTUAL MODEL.

    For now, this returns a placeholder question so that the rest of
    the pipeline (IDs, archiving, file writes) can be tested safely.

    Returned dict MUST include:
      - stem
      - option_a, option_b, option_c, option_d
      - correct_option (one of "A","B","C","D")
      - explanation
    """

    if difficulty == "easy":
        stem = (
            f"[EASY PLACEHOLDER] {topic} question in {cbc_category_label} "
            f"(replace with model-generated content)."
        )
    elif difficulty == "medium":
        stem = (
            f"[MEDIUM PLACEHOLDER] {topic} scenario in {cbc_category_label} "
            f"(replace with model-generated content)."
        )
    elif difficulty == "hard":
        stem = (
            f"[HARD PLACEHOLDER] {topic} multi-step scenario in {cbc_category_label} "
            f"with multiple CBC 11B references (replace with model-generated content)."
        )
    else:  # test_prep
        stem = (
            f"[TEST PREP PLACEHOLDER] Advanced exam-preparation scenario on {topic} in "
            f"{cbc_category_label}, with layered conditions and carefully designed "
            f"distractors consistent with CASp open-book exam style "
            f"(replace with model-generated content)."
        )

    return {
        "stem": stem,
        "option_a": "Option A (replace via model)",
        "option_b": "Option B (replace via model)",
        "option_c": "Option C (replace via model)",
        "option_d": "Option D (replace via model)",
        "correct_option": "B",
        "explanation": (
            f"Placeholder explanation for {cbc_category_label} / {topic} / {difficulty}. "
            f"Replace with a model-generated explanation that cites the relevant CBC 11B "
            f"sections and mirrors the wording style of official CASp exam questions."
        ),
    }


# ---------------------------------------------------------------------
# Test archive writer
# ---------------------------------------------------------------------


def archive_generated_test(
    exam_type: str,
    difficulty: str,
    topic: str,
    questions: List[Dict[str, Any]],
) -> Path:
    """
    Write a frozen snapshot of this generated test to disk.
    Category mix is captured inside each question record.
    """
    ensure_directories()

    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f"test-{exam_type}-{difficulty}-{ts}.json"
    path = OPEN_BOOK_TESTS_DIR / filename

    archive_payload = {
        "exam_type": exam_type,
        "difficulty": difficulty,
        "topic": topic,
        "generated_at_utc": ts,
        "num_questions": len(questions),
        "questions": questions,
    }

    # Save only the questions list for reuse by the generator
    save_json_list(path, archive_payload["questions"])

    # Save metadata next to it
    meta_path = path.with_suffix(".meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(archive_payload, f, ensure_ascii=False, indent=2)

    return path


# ---------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------


def generate_questions_for_run(
    *,
    exam_type: str,
    difficulty: str,
    topic: str,
    num_questions: int,
) -> None:
    authored_bank = load_json_list(AUTHORED_BANK_PATH)
    generated_bank = load_json_list(GENERATED_BANK_PATH)

    if not authored_bank:
        raise FileNotFoundError(
            f"No authored open-book bank found at {AUTHORED_BANK_PATH}."
        )

    difficulty = difficulty.strip().lower()
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(f"Invalid difficulty: {difficulty}. Must be one of {sorted(VALID_DIFFICULTIES)}")

    # Enforce open-book max 40 questions
    if exam_type == "open_book" and num_questions > OPEN_BOOK_MAX_QUESTIONS:
        print(
            f"Requested {num_questions} questions, but open-book maximum is "
            f"{OPEN_BOOK_MAX_QUESTIONS}. Limiting to {OPEN_BOOK_MAX_QUESTIONS}."
        )
        num_questions = OPEN_BOOK_MAX_QUESTIONS

    if num_questions <= 0:
        raise ValueError("num_questions must be > 0")

    existing_ids = collect_existing_ids(authored_bank, generated_bank)
    existing_stems = collect_all_stems(authored_bank, generated_bank)

    new_questions: List[Dict[str, Any]] = []

    for i in range(num_questions):
        # Pick a random CASp open-book category (CBC 11B division)
        cat_def = pick_random_casp_category()
        cbc_category_code = cat_def["code"]
        cbc_category_label = cat_def["label"]

        # Authored references for this band/category to guide style
        authored_refs = filter_authored_by_category_and_difficulty(
            authored_bank,
            cbc_category=cbc_category_code,
            difficulty=difficulty,
        )
        if authored_refs:
            sample_size = min(2, len(authored_refs))
            reference_questions = random.sample(authored_refs, sample_size)
        else:
            reference_questions = []

        reference_snippets: List[str] = []

        model_output = call_model_to_generate_question(
            exam_type=exam_type,
            difficulty=difficulty,
            cbc_category_code=cbc_category_code,
            cbc_category_label=cbc_category_label,
            topic=topic,
            reference_snippets=reference_snippets,
            reference_questions=reference_questions,
        )

        stem = model_output.get("stem", "")
        if is_too_similar(stem, existing_stems):
            print(
                f"Generated stem for question {i+1} looks too similar to an existing one. "
                f"Skipping this question."
            )
            continue

        qid = next_generated_id(existing_ids, exam_type=exam_type)
        existing_ids.add(qid)
        existing_stems.append(stem)

        question_record = {
            "id": qid,
            "exam_type": exam_type,
            "topic": topic,
            # CBC category in exam-metrics style
            "cbc_category": cbc_category_code,
            "cbc_category_label": cbc_category_label,
            "difficulty": difficulty,
            "text": stem,
            "stem": stem,
            "option_a": model_output.get("option_a", ""),
            "option_b": model_output.get("option_b", ""),
            "option_c": model_output.get("option_c", ""),
            "option_d": model_output.get("option_d", ""),
            "correct_option": model_output.get("correct_option", "B"),
            "explanation": model_output.get("explanation", ""),
            "source": "generated",
            "created_at_utc": datetime.utcnow().isoformat(),
        }

        new_questions.append(question_record)
        generated_bank.append(question_record)

    if not new_questions:
        print("No new questions were generated.")
        return

    save_json_list(GENERATED_BANK_PATH, generated_bank)

    archive_path = archive_generated_test(
        exam_type=exam_type,
        difficulty=difficulty,
        topic=topic,
        questions=new_questions,
    )

    print(f"Generated {len(new_questions)} new {difficulty} question(s) for topic '{topic}'.")
    print(f"Updated generated bank at: {GENERATED_BANK_PATH}")
    print(f"Archived this batch as a test at: {archive_path}")
    print(f"Metadata for this test at: {archive_path.with_suffix('.meta.json')}")


# ---------------------------------------------------------------------
# Simple CLI interface
# ---------------------------------------------------------------------


def main() -> None:
    print("=== CASp Open-Book Question Generator (v2) ===")
    print("This script writes to generated_open_book_questions.json")
    print("and archives each batch under generated_tests/open_book/")
    print("Open-book runs are limited to a maximum of 40 questions.")
    print("CBC 11B categories are assigned randomly using CASp exam-style buckets.")
    print()

    exam_type = "open_book"

    print("Choose difficulty:")
    print("  1) easy")
    print("  2) medium")
    print("  3) hard")
    print("  4) test_prep (advanced exam-preparation)")
    choice = input("Enter 1-4: ").strip()
    mapping = {"1": "easy", "2": "medium", "3": "hard", "4": "test_prep"}
    if choice not in mapping:
        print("Invalid choice. Exiting.")
        return
    difficulty = mapping[choice]

    topic = input("\nEnter a topic label (e.g., Parking, Routes, Restrooms): ").strip()
    if not topic:
        topic = "General"

    num_str = input(
        f"\nHow many new questions do you want to generate in this run? "
        f"(max {OPEN_BOOK_MAX_QUESTIONS} for open-book): "
    ).strip()
    try:
        num = int(num_str)
    except ValueError:
        print("Invalid number. Exiting.")
        return
    if num <= 0:
        print("Number must be > 0. Exiting.")
        return

    try:
        generate_questions_for_run(
            exam_type=exam_type,
            difficulty=difficulty,
            topic=topic,
            num_questions=num,
        )
    except Exception as e:
        print("Generation failed.")
        print(f"Reason: {e}")


if __name__ == "__main__":
    main()
