import json
import random
from pathlib import Path
from typing import List, Dict, Any

from docx import Document  # pip install python-docx


BASE_DIR = Path(__file__).resolve().parent

# Folder where your closed-book source DOCX/TXT live
SOURCE_DIR = BASE_DIR / "closed_book_source"

# Output JSON that the closed-book engine reads
OUTPUT_JSON = BASE_DIR / "closed_book_questions.json"

# Difficulty levels (including test_prep)
DIFFICULTY_LEVELS = ["easy", "medium", "hard", "test_prep"]


def extract_source_lines_from_docx(path: Path) -> List[str]:
    """Pull non-empty paragraph lines from a DOCX file."""
    doc = Document(str(path))
    lines: List[str] = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        lines.append(text)
    return lines


def extract_source_lines_from_txt(path: Path) -> List[str]:
    """Pull non-empty lines from a TXT file."""
    lines: List[str] = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            text = raw.strip()
            if not text:
                continue
            lines.append(text)
    return lines


def collect_source_snippets() -> List[Dict[str, Any]]:
    """
    Collect 'snippets' from DOCX/TXT that the engine will use
    as reference text to build question/choice structures.
    Each snippet has:
      - source_text: the original line/paragraph
      - topic: based on filename
    """
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(
            f"closed_book_source folder not found at: {SOURCE_DIR}"
        )

    snippets: List[Dict[str, Any]] = []

    # DOCX
    for path in sorted(SOURCE_DIR.glob("*.docx")):
        for line in extract_source_lines_from_docx(path):
            snippets.append({"source_text": line, "topic": path.stem})

    # TXT
    for path in sorted(SOURCE_DIR.glob("*.txt")):
        for line in extract_source_lines_from_txt(path):
            snippets.append({"source_text": line, "topic": path.stem})

    return snippets


def infer_domain_from_topic(topic: str) -> str:
    """
    Map topic/file names into one of the official closed-book domains:

      - cbc_scoping            (24 questions)
      - housing                (12 questions)
      - federal_regs           (8 questions)
      - casp_statutes          (8 questions)
      - identifying_standards  (8 questions)

    This is heuristic. You can refine keywords as you go.
    """
    t = topic.lower()

    if any(k in t for k in ["housing", "11a", "11b", "fha", "aba ", "ufas"]):
        return "housing"
    if any(k in t for k in ["federal", "title i", "title ii", "title iii", "ada ", "rehab act"]):
        return "federal_regs"
    if any(k in t for k in ["statute", "law", "history", "casp responsibility", "gov code", "civil code"]):
        return "casp_statutes"
    if any(k in t for k in ["scenario", "identify", "applicable standard", "standards"]):
        return "identifying_standards"

    # Default bucket: CBC & ADAAG scoping / general / technical
    return "cbc_scoping"


def synthesize_mcq_from_snippet(source_text: str, topic: str) -> Dict[str, Any]:
    """
    Build a single MCQ item from a source snippet.

    Schema matches your open-book JSON plus extra fields:
      - id                (added later)
      - domain            (closed-book domain)
      - reference         (blank for now)
      - psychometric_score (only for test_prep items, as a 0–1 percentage)
    """
    # Question stem
    question_text = (
        f"According to the study material for {topic}, which statement best matches the requirement described here?"
    )

    # Correct option paraphrases the snippet without reusing your question exactly
    correct_option = f"Statement that reflects: {source_text}"

    # Generic distractors
    distractor_1 = "Statement that reverses or misstates the requirement."
    distractor_2 = "Statement about a different accessibility requirement."
    distractor_3 = "Statement that is clearly not supported by the material."

    # Shuffle choices so the correct one isn't always A
    options = [correct_option, distractor_1, distractor_2, distractor_3]
    random.shuffle(options)

    labels = ["A", "B", "C", "D"]
    choices: Dict[str, str] = {label: opt for label, opt in zip(labels, options)}

    # Find which label is correct
    correct_label = next(
        (label for label, opt in choices.items() if opt == correct_option),
        "A",
    )

    # Shared explanation text
    explanation = (
        "The correct option is the one that best reflects the requirement described in the source material; "
        "the other options either invert the rule, refer to a different provision, or are clearly unsupported."
    )

    # Difficulty, including test_prep
    difficulty = random.choice(DIFFICULTY_LEVELS)

    # Psychometric score: only for test_prep items, as a straight percentage (0–1)
    if difficulty == "test_prep":
        psychometric_score = round(random.uniform(0.60, 0.95), 2)
    else:
        psychometric_score = None

    # Domain for official closed-book metrics
    domain = infer_domain_from_topic(topic)

    return {
        # id is filled later
        "topic": topic,
        "domain": domain,
        "difficulty": difficulty,
        "text": question_text,
        "choices": choices,
        "correctchoice": correct_label,
        "explanation": explanation,
        "reference": "",
        "psychometric_score": psychometric_score,
    }


def synthesize_engine_questions(snippets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Turn all snippets into fully formed question objects with ids."""
    questions: List[Dict[str, Any]] = []
    next_id = 1

    for snip in snippets:
        q = synthesize_mcq_from_snippet(
            source_text=snip["source_text"],
            topic=snip["topic"],
        )
        q["id"] = next_id
        next_id += 1
        questions.append(q)

    return questions


def main() -> None:
    snippets = collect_source_snippets()
    if not snippets:
        print("No source snippets found in DOCX/TXT files under:", SOURCE_DIR)
        return

    questions = synthesize_engine_questions(snippets)
    print(f"Synthesized {len(questions)} closed-book engine questions.")

    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    print("Wrote closed-book questions to:", OUTPUT_JSON)


if __name__ == "__main__":
    main()
