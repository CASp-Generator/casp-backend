from app.database import SessionLocal
from app.models import Question

def reset_questions():
    db = SessionLocal()
    try:
        deleted = db.query(Question).delete()
        db.commit()
        print(f"Deleted {deleted} questions")
    finally:
        db.close()

if __name__ == "__main__":
    reset_questions()
