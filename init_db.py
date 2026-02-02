# init_db.py
from sqlalchemy.orm import Session
from database import engine  # your existing engine
from models import Base, User  # your existing Base and User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def init():
    # 1) Create all tables (including "users")
    Base.metadata.create_all(bind=engine)

    # 2) Create a default user if it doesn't exist
    db = Session(bind=engine)
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
