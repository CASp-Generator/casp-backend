#!/usr/bin/env python
"""
Merge detailed explanations into the tagged open-book question bank.

Usage:

    1. Open Command Prompt.
    2. Change directory to the project folder:
       cd "C:\\Users\\Jas\\Documents\\CASp Generator\\Open Book\\casp_generator\\casp-rag"
    3. Run this script:
       python merge_explanations.py

This script expects:
  - open_book_questions_tagged.json in the current directory.
  - data\\open_book_explanations.json relative to the current directory.

For each question whose 'id' matches an 'id' in open_book_explanations.json,
the script adds or replaces the 'explanation' field in that question.
"""

import json
import os
from typing import Any, Dict, List

# Filenames (relative to the directory where you run this script)
QUESTION_BANK_PATH = "open_book_questions_tagged.json"
EXPLANATIONS_PATH = os.path.join("data", "open_book_explanations.json")


def load_json(path: str) -> Any:
    """Load JSON from a file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    """Save JSON to a file with pretty formatting."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def index_explanations_by_id(explanations: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Convert a list of explanation objects into a dictionary indexed by id.

    Input format example:
    [
      {"id": "CBC11B_2019_OB_0001", "explanation": "Explanation text..."},
      {"id": "CBC11B_2019_OB_0002", "explanation": "Explanation text..."}
    ]
    """
    result: Dict[str, str] = {}
    for item in explanations:
        qid = item.get("id")
        exp = item.get("explanation")
        if isinstance(qid, str) and isinstance(exp, str):
            result[qid] = exp
    return result


def merge_explanations(
    questions: List[Dict[str, Any]],
    explanations_by_id: Dict[str, str],
) -> int:
    """
    Attach explanations to questions by matching ids.

    Returns:
        Number of questions that were updated.
    """
    updated_count = 0

    for q in questions:
        qid = q.get("id")
        if isinstance(qid, str) and qid in explanations_by_id:
            q["explanation"] = explanations_by_id[qid]
            updated_count += 1

    return updated_count


def main() -> None:
    # Determine current working directory
    cwd = os.getcwd()
    print(f"Running merge_explanations.py in: {cwd}")

    # Build full paths to the JSON files
    question_bank_path = os.path.join(cwd, QUESTION_BANK_PATH)
    explanations_path = os.path.join(cwd, EXPLANATIONS_PATH)

    print(f"Loading tagged questions from: {question_bank_path}")
    questions = load_json(question_bank_path)

    print(f"Loading explanations from: {explanations_path}")
    explanations = load_json(explanations_path)

    if not isinstance(questions, list):
        raise TypeError("Expected questions JSON to be a list of question objects.")

    if not isinstance(explanations, list):
        raise TypeError("Expected explanations JSON to be a list (array) of objects.")

    explanations_by_id = index_explanations_by_id(explanations)
    print(f"Loaded {len(explanations_by_id)} explanations keyed by id.")

    updated_count = merge_explanations(questions, explanations_by_id)
    print(f"Updated explanations for {updated_count} questions.")
    missing_count = max(0, len(questions) - updated_count)
    print(f"Questions still missing explanations: {missing_count}")

    # Save the updated question bank back to the same file
    save_json(question_bank_path, questions)
    print(f"Updated tagged question bank written to: {question_bank_path}")


if __name__ == "__main__":
    main()
