import re
import unicodedata
import bcrypt
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import AdminUser, User


def hash_password(plain: str) -> str:
    # bcrypt has a 72-byte input limit; truncate defensively rather than error.
    return bcrypt.hashpw(plain.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except ValueError:
        return False


def slugify(text: str) -> str:
    """Turn a title into a URL-safe slug, e.g. 'My Post!' -> 'my-post'."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def get_current_admin(request: Request, db: Session = Depends(get_db)):
    """
    FastAPI dependency for protecting admin routes.
    Reads the logged-in admin's id from the signed session cookie.
    """
    user_id = request.session.get("admin_user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )
    admin = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )
    return admin


def get_optional_admin(request: Request, db: Session = Depends(get_db)):
    """Non-raising version — used to show/hide admin-only UI on public pages."""
    user_id = request.session.get("admin_user_id")
    if not user_id:
        return None
    return db.query(AdminUser).filter(AdminUser.id == user_id).first()


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    FastAPI dependency for protecting regular-user routes (e.g. /dashboard).
    Uses a separate session key from admin, so the two logins never overlap.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)):
    """Non-raising version — used to show/hide user-only UI (nav, hero CTA)."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()
