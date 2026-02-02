"""
Improved auto-tagging of difficulty for open_book_questions.json.

Heuristics use:
- Length of stem
- Count of CBC/code references
- Presence of bullets/steps
- Scenario/exam-style wording

Outputs: open_book_questions_tagged.json with difficulty in:
- easy, medium, hard, test_prep

Also ensures each question has a CBC 11B category aligned with CASp
open-book exam metrics (Div 2 + 5/8, 4, 6, 7, 9).
"""

from pathlib import Path
import json
import re

PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_PATH = PROJECT_ROOT / "open_book_questions.json"
OUTPUT_PATH = PROJECT_ROOT / "open_book_questions_tagged.json"

# Rough patterns for code references – tune to your CASp content
CBC_PATTERN = re.compile(r"\b11[A-Z]?\b|\b20[1-9]\b|\b30[1-9]\b")
SECTION_PATTERN = re.compile(r"\bSection\s+\d+[A-Za-z0-9.-]*")

# Valid open-book CBC 11B categories, aligned with DSA metrics F–J
# F: Div 2 + 5/8 Site & EV
# G: Div 2 + 4 Routes
# H: Div 2 + 6 Plumbing
# I: Div 2 + 7 Communication
# J: Div 2 + 9 Built-Ins
VALID_OPEN_BOOK_CATEGORIES = {
    "11B-5/8",  # site / parking / EVCS
    "11B-4",    # accessible routes
    "11B-6",    # plumbing elements / facilities
    "11B-7",    # communication
    "11B-9",    # built-ins / features
}


def count_code_refs(text: str) -> int:
    if not text:
        return 0
    return len(CBC_PATTERN.findall(text)) + len(SECTION_PATTERN.findall(text))


def has_list_structure(text: str) -> bool:
    if not text:
        return False
    return any(
        marker in text
        for marker in [
            "\n- ",
            "\n* ",
            "\n1. ",
            "\n2. ",
            "\n3. ",
            " A.",
            " B.",
            " C.",
        ]
    )


SCENARIO_KEYWORDS = [
    "clinic",
    "spinal",
    "rehabilitation",
    "doctor",
    "patient",
    "waiting room",
    "exam room",
    "suite",
    "tenant space",
    "tenant improvement",
    "shell building",
    "multi-story",
    "multi-storey",
    "shopping center",
    "grocery",
    "restaurant",
    "parking facility",
    "parking structure",
    "parking garage",
    "apartment",
    "hotel",
    "motel",
    "lodging",
    "field office",
    "customer service center",
]


EXAM_STYLE_MARKERS = [
    "most appropriate",
    "best describes",
    "best meets",
    "which of the following",
    "based on the information above",
    "based on this scenario",
    "you are reviewing plans",
    "you are inspecting",
    "plan review",
    "project type",
    "new spinal care clinic",
    "new title ii field office",
]


def is_scenario(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(k in lower for k in SCENARIO_KEYWORDS)


def is_exam_style(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(k in lower for k in EXAM_STYLE_MARKERS)


def estimate_difficulty(text: str) -> str:
    """
    Multi-factor heuristic:
    - Short, few code refs, no scenario -> easy
    - Medium length, modest refs or light scenario -> medium
    - Long, many refs, or heavy scenario/exam-style -> hard
    """
    if not text:
        return "medium"

    t = text.strip()
    length = len(t)
    refs = count_code_refs(t)
    listy = has_list_structure(t)
    scenario = is_scenario(t)
    examy = is_exam_style(t)

    # Strong hard signals
    if length > 350 or refs >= 4 or (scenario and examy) or (scenario and refs >= 2):
        return "hard"

    # Clear easy signals
    if length < 140 and refs <= 1 and not scenario and not listy:
        return "easy"

    # Mild hard signals
    if (length > 260 and (scenario or refs >= 2)) or (listy and (scenario or refs >= 2)):
        return "hard"

    # Default
    return "medium"


def is_test_prep_candidate(text: str, base_difficulty: str) -> bool:
    """
    Upgrade a subset of hard items that look like full exam scenarios to test_prep.

    Tuned to be closer to CASp open-book exam items:
    - Only consider items already estimated as hard
    - Require scenario/exam-style wording and multiple code refs,
      or explicit "packet" markers.
    """
    if not text or base_difficulty != "hard":
        return False

    t = text.strip()
    lower = t.lower()
    refs = count_code_refs(t)
    scenario = is_scenario(t)
    examy = is_exam_style(t)

    long_enough = len(t) > 260
    very_long = len(t) > 340

    packet_markers = [
        "detail set",
        "enlarged plan",
        "exam-style",
        "test prep",
        "packet",
    ]
    has_packet_markers = any(k in lower for k in packet_markers)

    # Stricter, exam-aligned rules:
    return (
        has_packet_markers
        or (very_long and scenario and refs >= 2)
        or (long_enough and scenario and examy and refs >= 2)
        or (scenario and examy and refs >= 3)
    )


def normalize_category(q: dict) -> str:
    """
    Ensure each question has a CBC 11B category aligned with the
    CASp open-book testing categories (Div 2 + 5/8, 4, 6, 7, 9).

    If the question already has a category, keep it if valid.
    Otherwise, set a default or auto-guess based on keywords.
    """
    cat = (q.get("category") or "").strip()
    if cat in VALID_OPEN_BOOK_CATEGORIES:
        return cat

    text = (q.get("text") or "").lower()

    # Very rough heuristics to guess category
    if any(k in text for k in ["parking", "stall", "lot", "drive aisle", "loading", "site", "evcs", "electric vehicle"]):
        cat = "11B-5/8"
    elif any(k in text for k in ["route", "path of travel", "walk", "ramp", "stair", "stairs", "elevator", "lift"]):
        cat = "11B-4"
    elif any(k in text for k in ["toilet", "restroom", "lavatory", "shower", "bath", "urinal", "grab bar", "bathtub"]):
        cat = "11B-6"
    elif any(k in text for k in ["sign", "tactile", "braille", "alarm", "communication", "assistive listening", "public address"]):
        cat = "11B-7"
    elif any(k in text for k in ["counter", "work surface", "storage", "shelf", "bench", "drinking fountain", "fixed seating"]):
        cat = "11B-9"
    else:
        cat = "UNASSIGNED"

    q["category"] = cat
    return cat


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input question bank not found at: {INPUT_PATH}")

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)

    tagged_questions = []
    easy_count = medium_count = hard_count = test_prep_count = 0

    for q in questions:
        text = q.get("text", "") or ""

        # Always re-estimate difficulty from text; ignore existing tags
        difficulty = estimate_difficulty(text)

        if is_test_prep_candidate(text, difficulty):
            difficulty = "test_prep"
            test_prep_count += 1
        elif difficulty == "easy":
            easy_count += 1
        elif difficulty == "medium":
            medium_count += 1
        elif difficulty == "hard":
            hard_count += 1

        q["difficulty"] = difficulty

        # Ensure we have a CBC 11B category aligned with CASp metrics
        normalize_category(q)

        tagged_questions.append(q)

    print(f"Total questions: {len(tagged_questions)}")
    print(f"Easy: {easy_count}")
    print(f"Medium: {medium_count}")
    print(f"Hard: {hard_count}")
    print(f"Test Prep: {test_prep_count}")
    if tagged_questions:
        print(f"Sample first question difficulty: {tagged_questions[0].get('difficulty')}")
        print(f"Sample first question category: {tagged_questions[0].get('category')}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(tagged_questions, f, ensure_ascii=False, indent=2)

    print(f"Tagged question bank written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
