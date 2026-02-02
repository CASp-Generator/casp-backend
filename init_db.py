from sqlalchemy.orm import Session

from database import engine, SessionLocal
from models import Base, User


def init():
    # Create all tables
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        email = "test@example.com"
        existing = db.query(User).filter(User.email == email).first()
        if not existing:
            user = User(
                email=email,
                # TEMP: plain-text password to avoid bcrypt issues on Render
                password="testpassword123",
                is_admin=True,
                has_active_subscription=True,
            )
            db.add(user)
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    init()
