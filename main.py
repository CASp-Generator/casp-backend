from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Literal, List
import json
import random
from pathlib import Path

from .models import SessionLocal, Question
from . import test_prep_results
from .auth import get_current_user, UserBase, login_for_access_token

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(test_prep_results.router)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class ExamRequest(BaseModel):
    mode: Literal["open", "closed", "mixed"]
    count: int
    difficulty: Literal["easy", "medium", "hard", "test_prep"] | None = None


class ExamQuestion(BaseModel):
    id: int
    text: str
    correct_answer: str
    qtype: Literal["open", "closed"] | None = None
    difficulty: str | None = None
    reference_document: str | None = None
    reference_section: str | None = None


class ExamResponse(BaseModel):
    mode: Literal["open", "closed", "mixed"]
    count: int
    questions: List[ExamQuestion]


class MeResponse(BaseModel):
    id: int
    email: str
    has_active_subscription: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def clamp(n: int, minimum: int, maximum: int) -> int:
    if n < minimum:
        return minimum
    if n > maximum:
        return maximum
    return n


def _map_question(q) -> ExamQuestion:
    return ExamQuestion(
        id=q.id,
        text=q.text,
        correct_answer=q.correct_answer,
        qtype=(
            getattr(q, "qtype", None).value
            if getattr(q, "qtype", None) is not None
            else None
        ),
        difficulty=(
            getattr(q, "difficulty", None).value
            if getattr(q, "difficulty", None) is not None
            else None
        ),
        reference_document=getattr(q, "reference_document", None),
        reference_section=getattr(q, "reference_section", None),
    )


def build_mixed_exam(total_count: int, difficulty: str | None = None):
    db = SessionLocal()
    try:
        open_count = round(total_count * 0.4)
        closed_count = total_count - open_count

        if total_count >= 2:
            if open_count == 0:
                open_count = 1
                closed_count = total_count - open_count
            if closed_count == 0:
                closed_count = 1
                open_count = total_count - closed_count

        base_open = db.query(Question).filter(Question.qtype == "open")
        base_closed = db.query(Question).filter(Question.qtype == "closed")

        open_query = base_open
        closed_query = base_closed
        if difficulty is not None:
            open_query = open_query.filter(Question.difficulty == difficulty)
            closed_query = closed_query.filter(Question.difficulty == difficulty)

        open_questions = open_query.limit(open_count).all()
        closed_questions = closed_query.limit(closed_count).all()

        if not open_questions and not closed_questions and difficulty is not None:
            open_questions = base_open.limit(open_count).all()
            closed_questions = base_closed.limit(closed_count).all()

        questions = open_questions + closed_questions
        effective_count = len(questions)

        if effective_count == 0:
            raise HTTPException(
                status_code=400,
                detail="No questions available for requested difficulty/mode mix",
            )

        result_questions = [_map_question(q) for q in questions]

        return effective_count, result_questions
    finally:
        db.close()


def build_closed_test_prep_exam(count: int) -> tuple[int, List[ExamQuestion]]:
    """
    Closed-book Test Prep exam from authored JSON bank.
    Loads from closed_book_questions.json and samples up to `count` questions.
    """
    json_path = Path(__file__).resolve().parent.parent / "closed_book_questions.json"
    if not json_path.exists():
        raise HTTPException(status_code=500, detail="Closed-book question bank not found")

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Filter to difficulty == "test_prep"
    pool = [q for q in data if q.get("difficulty") == "test_prep"]

    if not pool:
        raise HTTPException(
            status_code=400,
            detail="No closed-book test prep questions available in JSON bank",
        )

    # Shuffle and sample up to requested count
    random.shuffle(pool)
    selected = pool[:count]

    questions: List[ExamQuestion] = []
    for q in selected:
        questions.append(
            ExamQuestion(
                id=q["id"],
                text=q["text"],
                correct_answer=q["correctchoice"],
                qtype="closed",
                difficulty=q.get("difficulty"),
                reference_document=q.get("reference"),
                reference_section=None,
            )
        )

    return len(questions), questions


@app.post("/exam", response_model=ExamResponse)
def create_exam(payload: ExamRequest, user: UserBase = Depends(get_current_user)):
    # Mixed mode: still uses DB (open + closed)
    if payload.mode == "mixed":
        effective_count, result_questions = build_mixed_exam(
            total_count=payload.count,
            difficulty=payload.difficulty,
        )
        return ExamResponse(
            mode="mixed",
            count=effective_count,
            questions=result_questions,
        )

    # Clamp counts
    if payload.mode == "open":
        min_q, max_q = 1, 40
    else:
        min_q, max_q = 1, 60

    clamped_count = clamp(payload.count, min_q, max_q)

    # Closed-book Test Prep: use JSON bank
    if payload.mode == "closed" and payload.difficulty == "test_prep":
        effective_count, result_questions = build_closed_test_prep_exam(clamped_count)
        return ExamResponse(
            mode="closed",
            count=effective_count,
            questions=result_questions,
        )

    # All other cases: use DB questions table
    db = SessionLocal()
    try:
        base_query = db.query(Question)

        if payload.mode == "closed":
            base_query = base_query.filter(Question.qtype == "closed")
        elif payload.mode == "open":
            base_query = base_query.filter(Question.qtype == "open")

        query = base_query
        if payload.difficulty is not None:
            query = query.filter(Question.difficulty == payload.difficulty)

        questions = query.limit(clamped_count).all()

        if not questions and payload.difficulty is not None:
            questions = base_query.limit(clamped_count).all()
    finally:
        db.close()

    if not questions:
        raise HTTPException(status_code=400, detail="No questions available")

    result_questions = [_map_question(q) for q in questions]
    effective_count = min(clamped_count, len(result_questions))

    return ExamResponse(
        mode=payload.mode,
        count=effective_count,
        questions=result_questions,
    )


@app.post("/api/auth/login", response_model=TokenResponse)
def login_endpoint(form_data: OAuth2PasswordRequestForm = Depends()):
    return login_for_access_token(form_data)


@app.get("/api/auth/me", response_model=MeResponse)
def read_me(user: UserBase = Depends(get_current_user)):
    return MeResponse(
        id=user.id,
        email=user.email,
        has_active_subscription=user.has_active_subscription,
    )
