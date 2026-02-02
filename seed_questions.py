from app.models import (
    Base,
    Question,
    DifficultyBandDB,
    QuestionTypeDB,
    QuestionDifficultyDB,
    engine,
    SessionLocal,
)


def seed():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Clear existing questions so we don't keep duplicating
        db.query(Question).delete()

        questions: list[Question] = []

        # 20 open-book questions
        for i in range(1, 21):
            is_easy = i <= 10
            questions.append(
                Question(
                    text=f"Sample open-book question {i}",
                    correct_answer="A",
                    band=DifficultyBandDB.TestPrep,
                    topic="Sample Open",
                    source_code="GEN",
                    source_section=str(i),
                    source_note="Seeded open-book sample",
                    subject="CASp",
                    qtype=QuestionTypeDB.Open,
                    difficulty=(
                        QuestionDifficultyDB.Easy if is_easy else QuestionDifficultyDB.Medium
                    ),
                    tags="sample,open,medium",
                    # Easy–Guided: where the answer lives
                    reference_document=(
                        "CBC Chapter 11B – Sample Guide" if is_easy else None
                    ),
                    reference_section=(f"Section OB-{i:02d}" if is_easy else None),
                )
            )

        # 20 closed-book questions
        for i in range(1, 21):
            is_easy = i <= 10
            questions.append(
                Question(
                    text=f"Sample closed-book question {i}",
                    correct_answer="A",
                    band=DifficultyBandDB.TestPrep,
                    topic="Sample Closed",
                    source_code="GEN",
                    source_section=str(100 + i),
                    source_note="Seeded closed-book sample",
                    subject="CASp",
                    qtype=QuestionTypeDB.Closed,
                    difficulty=(
                        QuestionDifficultyDB.Easy if is_easy else QuestionDifficultyDB.Medium
                    ),
                    tags="sample,closed,medium",
                    # Easy–Guided: where the answer lives
                    reference_document=(
                        "CBC Chapter 11B – Sample Guide" if is_easy else None
                    ),
                    reference_section=(f"Section CB-{i:02d}" if is_easy else None),
                )
            )

        db.add_all(questions)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
