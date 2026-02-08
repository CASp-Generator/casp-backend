# C:\Users\Jas\Documents\CASp Generator\Open Book\casp_backend_clean\seed_users_render.py
from models import SessionLocal, User, Base, engine


def main() -> None:
    # Ensure tables exist (users, questions, etc.)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Admin user
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        if not admin:
            admin = User(
                email="admin@example.com",
                password="admin123",
                is_admin=True,
                has_active_subscription=True,
            )
            db.add(admin)

        # Regular user
        user = db.query(User).filter(User.email == "user@example.com").first()
        if not user:
            user = User(
                email="user@example.com",
                password="user123",
                is_admin=False,
                has_active_subscription=False,
            )
            db.add(user)

        db.commit()

        print("Seeded users in Render DB (or they already existed):")
        all_users = db.query(User).all()
        for u in all_users:
            print(
                f"- {u.id} {u.email} is_admin={u.is_admin} "
                f"has_active_subscription={u.has_active_subscription}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
