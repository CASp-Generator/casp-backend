from datetime import datetime
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel

ExamType = Literal["open_book", "closed_book", "mixed"]
ExamMode = Literal["official_like", "test_prep"]


class DomainResult(BaseModel):
    """
    Result for a single domain/category within one exam attempt.
    Example domain_code values (you can standardize these in your UI):
      Closed-book:
        - CBC_ADAAG
        - HOUSING
        - FEDERAL_REGS
        - CASP_RESPONSIBILITY
        - APPLICABLE_STANDARDS
      Open-book:
        - F_SITE_ELEMENTS_EV
        - G_ROUTES
        - H_PLUMBING
        - I_COMMUNICATION
        - J_BUILT_IN
    """
    domain_code: str
    questions_in_domain: int
    correct_in_domain: int


class ExamAttempt(BaseModel):
    """
    Minimal structure for computing raw percent and psychometric scores.

    NOTE:
    - raw_percent is not stored here; it is computed as needed.
    - psychometric_score is returned by functions, not stored here.
    """
    exam_id: int
    exam_type: ExamType
    mode: ExamMode
    taken_at: datetime
    total_questions: int
    total_correct: int
    domains: List[DomainResult]


# ---- Hard-coded domain weights ----

CLOSED_BOOK_WEIGHTS: Dict[str, float] = {
    # 24 questions total
    "CBC_ADAAG": 0.30,
    # 12 questions
    "HOUSING": 0.20,
    # 8 questions
    "FEDERAL_REGS": 0.20,
    # 8 questions
    "CASP_RESPONSIBILITY": 0.15,
    # 8 questions
    "APPLICABLE_STANDARDS": 0.15,
}

OPEN_BOOK_WEIGHTS: Dict[str, float] = {
    # Project-type categories F–J from your metrics
    "F_SITE_ELEMENTS_EV": 0.25,
    "G_ROUTES": 0.20,
    "H_PLUMBING": 0.20,
    "I_COMMUNICATION": 0.15,
    "J_BUILT_IN": 0.20,
}


def compute_raw_percent(total_correct: int, total_questions: int) -> Optional[float]:
    """
    Raw percent score (0–100) for any exam (prep or non-prep).
    Returns None if total_questions is 0 or negative.
    """
    if total_questions <= 0:
        return None
    return (total_correct / total_questions) * 100.0


def _get_weights_for_exam_type(exam_type: ExamType) -> Optional[Dict[str, float]]:
    if exam_type == "closed_book":
        return CLOSED_BOOK_WEIGHTS
    if exam_type == "open_book":
        return OPEN_BOOK_WEIGHTS
    # For now, no psychometric for mixed; you can add later if desired.
    return None


def compute_psychometric_score_for_exam(
    exam: ExamAttempt,
    alpha: float = 0.4,
) -> Optional[float]:
    """
    Psychometric score (0–100) for a single exam attempt.

    Rules:
      - Only computed for mode == "test_prep".
      - Uses hard-coded domain weights per exam type.
      - If no domain data, falls back to raw percent.
      - Mixed exams currently return None (you can define later).

    alpha:
      - 0.4 means 40% weight on raw percent, 60% on domain-balanced performance.
    """
    if exam.mode != "test_prep":
        return None

    if exam.total_questions <= 0:
        return None

    raw_percent = compute_raw_percent(exam.total_correct, exam.total_questions)
    if raw_percent is None:
        return None

    weights = _get_weights_for_exam_type(exam.exam_type)
    if weights is None:
        # No psychometric defined for this type
        return None

    # Compute per-domain percentages
    domain_scores: Dict[str, float] = {}
    for d in exam.domains:
        if d.questions_in_domain <= 0:
            continue
        domain_scores[d.domain_code] = (d.correct_in_domain / d.questions_in_domain) * 100.0

    # If no domain scores, just return raw percent
    if not domain_scores:
        return max(0.0, min(100.0, raw_percent))

    # Weighted composite using only domains that appear in this exam
    domain_composite = 0.0
    total_weight = 0.0
    for code, w in weights.items():
        if code in domain_scores:
            domain_composite += w * domain_scores[code]
            total_weight += w

    if total_weight > 0:
        domain_composite /= total_weight
    else:
        domain_composite = raw_percent

    score = alpha * raw_percent + (1.0 - alpha) * domain_composite
    return max(0.0, min(100.0, score))


def compute_psychometric_proficiency_for_type(
    attempts: List[ExamAttempt],
    exam_type: ExamType,
    alpha: float = 0.4,
) -> Optional[float]:
    """
    Longitudinal (multi-attempt) psychometric proficiency for a given exam type.

    - Filters to test-prep attempts of the given exam_type.
    - Uses at most the last 3 attempts, recency-weighted.
    - Returns a single 0–100 score, or None if not enough data.
    """
    filtered = [
        a for a in attempts
        if a.exam_type == exam_type and a.mode == "test_prep"
    ]
    if not filtered:
        return None

    # Sort by date ascending and take up to last 3
    filtered.sort(key=lambda a: a.taken_at)
    recent = filtered[-3:]

    # Recency weights for up to 3 exams: oldest->newest = 0.2, 0.3, 0.5
    base_weights = [0.2, 0.3, 0.5]
    weights = base_weights[-len(recent):]
    total_w = sum(weights)
    weights = [w / total_w for w in weights] if total_w > 0 else [1.0 / len(recent)] * len(recent)

    scores: List[float] = []
    for exam in recent:
        s = compute_psychometric_score_for_exam(exam, alpha=alpha)
        if s is not None:
            scores.append(s)

    if not scores:
        return None

    # If some attempts had no psychometric (should not happen for test_prep), use weights matching count
    effective_weights = weights[-len(scores):] if len(scores) < len(weights) else weights

    proficiency = sum(w * s for w, s in zip(effective_weights, scores))
    return max(0.0, min(100.0, proficiency))
