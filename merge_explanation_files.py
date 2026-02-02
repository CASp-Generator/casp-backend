#!/usr/bin/env python
"""
Merge one or more per-exam explanation JSON files into the global
data\\open_book_explanations.json, handling commas/duplicates automatically.

Usage example:

  cd "C:\\Users\\Jas\\Documents\\CASp Generator\\Open Book\\casp_generator\\casp-rag"
  python merge_explanation_files.py spinal_clinic_explanations.json

You can pass multiple files:

  python merge_explanation_files.py spinal_clinic_explanations.json simulation1_explanations.json
"""

import json
from pathlib import Path
from typing import Dict, Any, List
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
GLOBAL_EXPL_PATH = PROJECT_ROOT / "data" / "open_book_explanations.json"


def load_json_list(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return []


def save_json_list(path: Path, data: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def index_by_id(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for obj in items:
        qid = obj.get("id")
        if isinstance(qid, str):
            result[qid] = obj
    return result


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python merge_explanation_files.py <file1.json> [file2.json ...]")
        sys.exit(1)

    input_files = sys.argv[1:]

    global_items = load_json_list(GLOBAL_EXPL_PATH)
    global_index = index_by_id(global_items)
    print(f"Loaded {len(global_items)} existing global explanations from {GLOBAL_EXPL_PATH}")

    added_count = 0
    updated_count = 0

    for name in input_files:
        src_path = PROJECT_ROOT / name
        print(f"Reading explanations from: {src_path}")
        items = load_json_list(src_path)
        print(f"  Found {len(items)} items.")
        for obj in items:
            qid = obj.get("id")
            if not isinstance(qid, str):
                continue
            if qid in global_index:
                # Overwrite existing entry for that id
                global_index[qid] = obj
                updated_count += 1
            else:
                global_index[qid] = obj
                added_count += 1

    merged_list = list(global_index.values())
    merged_list.sort(key=lambda o: o.get("id", ""))

    save_json_list(GLOBAL_EXPL_PATH, merged_list)
    print(f"Global explanations now has {len(merged_list)} items.")
    print(f"Added {added_count} new ids, updated {updated_count} existing ids.")
    print(f"Wrote merged explanations to: {GLOBAL_EXPL_PATH}")


if __name__ == "__main__":
    main()
