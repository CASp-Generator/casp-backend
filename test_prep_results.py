from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Literal, Optional
from .auth import get_current_user, UserBase
from .models import SessionLocal, Question

router = APIRouter()


class OpenBookAnswer(BaseModel):
    question_id: int
    choice: str


class ClosedBookAnswer(BaseModel):
    question_id: int
    choice: str


class MixedAnswer(BaseModel):
    question_id: int
    kind: Literal["open_book", "closed_book"]
    choice: str


class BaseResult(BaseModel):
    correct: int
    total_questions: int
    percent: float
    raw_percent: Optional[float] = None
    # For Test Prep, this is your Psychometric Mastery Score (0–100).
    psychometric_score: Optional[float] = None


class OpenBookWrongAnswer(BaseModel):
    question_id: int
    text: str = "Placeholder question text"
    user_choice: str
    correct_choice: str = "A"
    explanation: str = "Detailed explanation will go here later."


class ClosedBookWrongAnswer(BaseModel):
    question_id: int
    text: str = "Placeholder question text"
    user_choice: str
    correct_choice: str = "A"
    explanation: str = "Detailed explanation will go here later."


class MixedWrongAnswer(BaseModel):
    question_id: int
    kind: Literal["open_book", "closed_book"]
    text: str = "Placeholder question text"
    user_choice: str
    correct_choice: str = "A"
    explanation: Optional[str] = "Detailed explanation will go here later."


class OpenBookResult(BaseResult):
    wrong_answers: List[OpenBookWrongAnswer]


class ClosedBookResult(BaseResult):
    wrong_answers: List[ClosedBookWrongAnswer]


class MixedResult(BaseResult):
    wrong_answers: List[MixedWrongAnswer]


def _simple_percent(total: int, correct: int) -> float:
    if total <= 0:
        return 0.0
    return (correct / total) * 100.0


DOMAIN_WEIGHTS = {
    "cbc_scoping": 0.40,
    "housing": 0.20,
    "federal_regs": 0.1333,
    "casp_statutes": 0.1333,
    "identifying_standards": 0.1333,
}


def _compute_closed_book_mastery(db: SessionLocal, answers: List[ClosedBookAnswer]) -> float:
    if not answers:
        return 0.0

    q_ids = [a.question_id for a in answers]
    questions = (
        db.query(Question)
        .filter(Question.id.in_(q_ids))
        .all()
    )
    by_id = {q.id: q for q in questions}

    domain_correct: dict[str, int] = {}
    domain_total: dict[str, int] = {}

    for a in answers:
        q = by_id.get(a.question_id)
        if not q:
            continue
        domain = getattr(q, "domain", None)
        if not domain:
            continue

        domain_total[domain] = domain_total.get(domain, 0) + 1
        if a.choice == q.correct_answer:
            domain_correct[domain] = domain_correct.get(domain, 0) + 1

    if not domain_total:
        return 0.0

    weighted_sum = 0.0
    total_weight = 0.0

    for domain, total in domain_total.items():
        correct = domain_correct.get(domain, 0)
        domain_percent = _simple_percent(total, correct)
        w = DOMAIN_WEIGHTS.get(domain, 0.0)
        if w <= 0.0:
            continue
        weighted_sum += domain_percent * w
        total_weight += w

    if total_weight <= 0.0:
        return 0.0

    return weighted_sum / total_weight


@router.post("/api/open-book/test-prep-results", response_model=OpenBookResult)
def open_book_results(
    answers: List[OpenBookAnswer],
    user: UserBase = Depends(get_current_user),
):
    total = len(answers)
    # Stub grading for now; later you can plug in real logic.
    correct = total // 2
    percent = _simple_percent(total, correct)

    wrong_answers: List[OpenBookWrongAnswer] = []
    for a in answers:
        wrong_answers.append(
            OpenBookWrongAnswer(
                question_id=a.question_id,
                user_choice=a.choice,
            )
        )

    # Test Prep: Psychometric Mastery Score present (simple 0–100 mirror for now).
    return OpenBookResult(
        correct=correct,
        total_questions=total,
        percent=percent,
        raw_percent=None,
        psychometric_score=percent,
        wrong_answers=wrong_answers,
    )


@router.post("/api/closed-book/test-prep-results", response_model=ClosedBookResult)
def closed_book_results(
    answers: List[ClosedBookAnswer],
    user: UserBase = Depends(get_current_user),
):
    total = len(answers)
    db = SessionLocal()
    try:
        q_ids = [a.question_id for a in answers]
        questions = (
            db.query(Question)
            .filter(Question.id.in_(q_ids))
            .all()
        )
        by_id = {q.id: q for q in questions}

        correct = 0
        wrong_answers: List[ClosedBookWrongAnswer] = []

        for a in answers:
            q = by_id.get(a.question_id)
            if not q:
                continue
            if a.choice == q.correct_answer:
                correct += 1
            else:
                wrong_answers.append(
                    ClosedBookWrongAnswer(
                        question_id=a.question_id,
                        text=q.text,
                        user_choice=a.choice,
                        correct_choice=q.correct_answer,
                        explanation=getattr(q, "source_note", "Detailed explanation will go here later."),
                    )
                )

        percent = _simple_percent(total, correct)
        mastery = _compute_closed_book_mastery(db, answers)
    finally:
        db.close()

    # Test Prep closed-book: Psychometric Mastery Score (domain-weighted).
    return ClosedBookResult(
        correct=correct,
        total_questions=total,
        percent=percent,
        raw_percent=None,
        psychometric_score=mastery,
        wrong_answers=wrong_answers,
    )


@router.post("/api/mixed/test-prep-results", response_model=MixedResult)
def mixed_results(
    answers: List[MixedAnswer],
    user: UserBase = Depends(get_current_user),
):
    total = len(answers)
    # Stub grading.
    correct = total // 2
    percent = _simple_percent(total, correct)

    wrong_answers: List[MixedWrongAnswer] = []
    for a in answers:
        wrong_answers.append(
            MixedWrongAnswer(
                question_id=a.question_id,
                kind=a.kind,
                user_choice=a.choice,
            )
        )

    # Test Prep mixed: Psychometric Mastery Score present (simple 0–100 mirror for now).
    return MixedResult(
        correct=correct,
        total_questions=total,
        percent=percent,
        raw_percent=None,
        psychometric_score=percent,
        wrong_answers=wrong_answers,
    )
