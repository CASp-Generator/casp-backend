from sqlalchemy.orm import Session
from passlib.context import CryptContext

from database import engine, SessionLocal
from models import Base, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def init():
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        email = "test@example.com"
        existing = db.query(User).filter(User.email == email).first()
        if not existing:
            user = User(
                email=email,
                password=get_password_hash("testpassword123"),
                is_admin=True,
                has_active_subscription=True,
            )
            db.add(user)
            db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    init()
