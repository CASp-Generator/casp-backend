from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user, UserBase
from models import SessionLocal, Question

router = APIRouter(prefix="/api/test-prep-results", tags=["test_prep_results"])


class AnswerItem(BaseModel):
    question_id: int
    selected_answer: str


class GradeRequest(BaseModel):
    mode: str
    answers: List[AnswerItem]


class GradedQuestion(BaseModel):
    id: int
    text: str
    correct_answer: str
    selected_answer: str
    is_correct: bool
    qtype: str | None = None
    difficulty: str | None = None
    reference_document: str | None = None
    reference_section: str | None = None
    explanation: str | None = None


class GradeResponse(BaseModel):
    mode: str
    total_questions: int
    correct_count: int
    score_percent: float
    questions: List[GradedQuestion]


@router.post("", response_model=GradeResponse)
def grade_test_prep_results(payload: GradeRequest, user: UserBase = Depends(get_current_user)):
    db = SessionLocal()
    try:
        question_ids = [a.question_id for a in payload.answers]
        if not question_ids:
            raise HTTPException(status_code=400, detail="No answers submitted")

        questions = (
            db.query(Question)
            .filter(Question.id.in_(question_ids))
            .all()
        )

        question_map = {q.id: q for q in questions}

        graded_items: List[GradedQuestion] = []
        correct_count = 0

        for ans in payload.answers:
            q = question_map.get(ans.question_id)
            if not q:
                continue

            is_correct = (ans.selected_answer == q.correct_answer)
            if is_correct:
                correct_count += 1

            graded_items.append(
                GradedQuestion(
                    id=q.id,
                    text=q.text,
                    correct_answer=q.correct_answer,
                    selected_answer=ans.selected_answer,
                    is_correct=is_correct,
                    qtype=(q.qtype.value if getattr(q, "qtype", None) is not None else None),
                    difficulty=(q.difficulty.value if getattr(q, "difficulty", None) is not None else None),
                    reference_document=getattr(q, "reference_document", None),
                    reference_section=getattr(q, "reference_section", None),
                    explanation=getattr(q, "explanation", None),
                )
            )

        total_questions = len(graded_items)
        if total_questions == 0:
            raise HTTPException(status_code=400, detail="No valid questions found for grading")

        score_percent = round((correct_count / total_questions) * 100, 1)

        return GradeResponse(
            mode=payload.mode,
            total_questions=total_questions,
            correct_count=correct_count,
            score_percent=score_percent,
            questions=graded_items,
        )
    finally:
        db.close()
