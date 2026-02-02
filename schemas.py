from typing import Dict, List, Optional
from pydantic import BaseModel


class OpenBookQuestionSchema(BaseModel):
    id: int
    text: str
    choices: Dict[str, str]
    correctchoice: str
    explanation: str
    reference: str


class OpenBookWrongAnswer(BaseModel):
    question_id: int
    text: str
    user_choice: str
    correct_choice: str
    # main explanation block (why correct, why user is wrong)
    explanation: str
    # optional extra detail for Test Prep “nightmare mode”
    detailed_explanation: Optional[str] = None
    # optional extra “side-quest” insight (related code section, similar rule, etc.)
    side_quest: Optional[str] = None


class OpenBookExamResultResponse(BaseModel):
    total_questions: int
    correct: int
    percent: float
    wrong_answers: List[OpenBookWrongAnswer]
