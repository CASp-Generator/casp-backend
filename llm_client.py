# llm_client.py

from typing import List, Dict, Any


def call_llm_for_question(topic: str, snippets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Stub LLM function that returns a single multiple-choice 'test_prep' question
    dict with the required fields:
      - topic
      - difficulty: 'test_prep'
      - text
      - choices (A–D)
      - correctchoice
      - explanation

    This is intentionally simple and deterministic so you can replace it later
    with a real LLM API call.
    """

    # Build a very basic question using the topic and snippet count
    snippet_count = len(snippets)
    snippet_sources = ", ".join(
        str(s.get("source", "snippet")) for s in snippets[:3]
    ) or "CBC 11B reference materials"

    question_text = (
        f"For CASp test preparation on the topic '{topic}', which choice best "
        f"reflects typical CBC 11B accessibility compliance requirements?"
    )

    choices = {
        "A": f"Follow only local practice, regardless of CBC 11B, for the topic '{topic}'.",
        "B": "Apply CBC 11B requirements only when a project includes new construction.",
        "C": "Apply applicable CBC 11B requirements to new construction, alterations, and path of travel obligations.",
        "D": "Rely solely on federal ADA standards and ignore CBC 11B."
    }

    correct_choice = "C"

    explanation = (
        f"For CASp test preparation, it is important to understand that CBC 11B "
        f"requirements apply to new construction and many alterations, and they can "
        f"trigger related path of travel obligations. This question was generated "
        f"from {snippet_count} retrieved CBC 11B snippet(s), including sources such as "
        f"{snippet_sources}."
    )

    question_dict = {
        "topic": topic,
        "difficulty": "test_prep",
        "text": question_text,
        "choices": choices,
        "correctchoice": correct_choice,
        "explanation": explanation,
    }

    return question_dict
