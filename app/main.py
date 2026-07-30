import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .database import Base, engine
from .routers import public, admin

app = FastAPI(title="CyberPy Labs")

# Session cookie secret — override via env var in production.
# Falls back to a dev-only value so `uvicorn app.main:app` works out of the box.
SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev-secret-change-me-in-production")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(public.router)
app.include_router(admin.router)


@app.on_event("startup")
def on_startup():
    # Safety net: ensures tables exist even if `python -m app.seed` wasn't run yet.
    # The admin user itself still needs to be created via `python -m app.seed`.
    Base.metadata.create_all(bind=engine)
