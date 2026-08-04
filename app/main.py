import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .database import Base, engine, SessionLocal
from .models import AdminUser
from .auth import hash_password
from .routers import public, admin, account

app = FastAPI(title="CyberPy Labs")

# Session cookie secret — override via env var in production.
# Falls back to a dev-only value so `uvicorn app.main:app` works out of the box.
SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev-secret-change-me-in-production")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(public.router)
app.include_router(admin.router)
app.include_router(account.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

    # Optional non-interactive admin creation, for hosts with no shell access
    # (e.g. Render's free tier). Set ADMIN_USERNAME + ADMIN_PASSWORD as env
    # vars and an admin account is created automatically on first boot if
    # none exists yet. Locally, prefer `python -m app.seed` instead.
    username = os.environ.get("ADMIN_USERNAME")
    password = os.environ.get("ADMIN_PASSWORD")
    if username and password:
        db = SessionLocal()
        try:
            if db.query(AdminUser).count() == 0:
                db.add(AdminUser(username=username, password_hash=hash_password(password)))
                db.commit()
        finally:
            db.close()
