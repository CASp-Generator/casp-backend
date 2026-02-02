# CASp Generator – Launch deploy notes

## Version

- Launch version: v1.0-launch
- Branch: main

## Backend stack

- FastAPI + Uvicorn
- SQLAlchemy + Pydantic v2
- Auth: JWT via python-jose, plain-text dev passwords from seed data for now
- DB: Local SQLite for dev, Postgres planned for production

## Environment config

- .env.local – for local dev (not committed, contains real secrets)
- .env.example – template with all required keys

Expected keys:

- DATABASE_URL – production Postgres URL
- JWT_SECRET – strong random secret for JWT signing
- CORS_ORIGINS – comma-separated list of allowed origins (local + production frontend)
- EMAIL_FROM – sender address for emails (future)
- EMAIL_SMTP_HOST / PORT / USER / PASSWORD – SMTP settings (future)

## Launch assumptions

- Question bank lives in the DB and/or JSON file shipped with v1.0-launch.
- Auth is simple email + password with seeded users.
- No background workers or cron jobs required at launch.
- Logs can go to stdout on the hosting platform.
