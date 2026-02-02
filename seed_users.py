from app.models import SessionLocal, User, init_db

def main():
    init_db()
    db = SessionLocal()

    def get_or_create(email, password, is_admin=False, has_active_subscription=True):
        u = db.query(User).filter_by(email=email).first()
        if u:
            return u
        u = User(
            email=email,
            password=password,
            is_admin=is_admin,
            has_active_subscription=has_active_subscription,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        return u

    admin = get_or_create("admin@example.com", "admin123", is_admin=True)
    user = get_or_create("user@example.com", "user123", is_admin=False)

    print("USERS:")
    for u in db.query(User).all():
        print(u.id, u.email, u.is_admin)

    db.close()

if __name__ == "__main__":
    main()
