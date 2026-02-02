from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Enum as SAEnum,
    Boolean,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

# Use your main CASp exam database (in this folder)
DATABASE_URL = "sqlite:///casp_exam_app.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class DifficultyBandDB(str, Enum):
    Beginner = "Beginner"
    Intermediate = "Intermediate"
    Advanced = "Advanced"
    TestPrep = "TestPrep"


class QuestionTypeDB(str, Enum):
    Open = "open"
    Closed = "closed"


class QuestionDifficultyDB(str, Enum):
    Easy = "easy"
    Medium = "medium"
    Hard = "hard"
    TestPrep = "test_prep"


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    correct_answer = Column(String, nullable=False)

    band = Column(SAEnum(DifficultyBandDB), nullable=False)

    topic = Column(String, nullable=True)
    source_code = Column(String, nullable=True)
    source_section = Column(String, nullable=True)
    source_note = Column(String, nullable=True)

    subject = Column(String, nullable=True)
    qtype = Column("type", SAEnum(QuestionTypeDB), nullable=True)
    difficulty = Column(SAEnum(QuestionDifficultyDB), nullable=True)
    tags = Column(String, nullable=True)

    # Easy–Guided: where the answer lives
    reference_document = Column(String, nullable=True)
    reference_section = Column(String, nullable=True)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    # NOTE: plain text password for now; later replace with hashed password
    password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    has_active_subscription = Column(Boolean, default=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
