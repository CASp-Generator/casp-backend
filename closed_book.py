from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from . import models, schemas, database
from .auth import get_current_user

router = APIRouter(prefix="/closed-book", tags=["closed-book"])

def build_closed_book_exam(count: int, difficulty: Optional[str], db: Session, user_id: int) -> List[models.Question]:
    """
    Build a closed-book exam with an optional difficulty filter.
    If difficulty is None, do not filter by difficulty.
    """
    query = db.query(models.Question).filter(
        models.Question.is_open_book == False,
        models.Question.owner_id == user_id
    )
    if difficulty:
        query = query.filter(models.Question.difficulty == difficulty)

    questions = query.order_by(models.Question.id).limit(count).all()

    if len(questions) < count:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough closed-book questions for difficulty={difficulty or 'ANY'}; requested {count}, found {len(questions)}."
        )

    return questions


@router.post("/generate", response_model=List[schemas.QuestionOut])
def generate_closed_book_exam(
    count: int,
    difficulty: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    API endpoint for generating a closed-book exam.
    Accepts count and optional difficulty.
    """
    questions = build_closed_book_exam(
        count=count,
        difficulty=difficulty,
        db=db,
        user_id=current_user.id
    )
    return questions
