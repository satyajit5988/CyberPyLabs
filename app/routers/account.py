import os
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CATEGORIES, CATEGORY_LABELS
from .. import crud
from ..auth import (
    hash_password,
    verify_password,
    get_optional_admin,
    get_optional_user,
    get_current_user,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

try:
    _ASSET_VERSION = str(int(os.path.getmtime("app/static/css/style.css")))
except OSError:
    _ASSET_VERSION = "1"
templates.env.globals["asset_version"] = _ASSET_VERSION


def ctx(request: Request, db: Session, **extra):
    admin_user = get_optional_admin(request, db)
    current_user = get_optional_user(request, db)
    base = {
        "request": request,
        "admin": admin_user,
        "user": current_user,
        "current_year": datetime.now(timezone.utc).year,
        "categories": CATEGORIES,
        "category_labels": CATEGORY_LABELS,
        "unread_message_count": crud.count_unread_messages(db) if admin_user else 0,
    }
    base.update(extra)
    return base


@router.get("/register")
def register_form(request: Request, db: Session = Depends(get_db)):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("register.html", ctx(
        request, db,
        active_nav="register",
        error=None,
        form_values={},
    ))


@router.post("/register")
def register_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(""),
    mobile: str = Form(""),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    name = name.strip()
    email = email.strip().lower()
    mobile = mobile.strip()
    form_values = {"name": name, "email": email, "mobile": mobile}

    error = None
    if not name:
        error = "Full name is required."
    elif not email and not mobile:
        error = "Enter an email address or mobile number."
    elif password != confirm_password:
        error = "Passwords do not match."
    elif len(password) < 8:
        error = "Password should be at least 8 characters."
    elif email and crud.get_user_by_identifier(db, email):
        error = "An account with this email already exists."
    elif mobile and crud.get_user_by_identifier(db, mobile):
        error = "An account with this mobile number already exists."

    if error:
        return templates.TemplateResponse("register.html", ctx(
            request, db,
            active_nav="register",
            error=error,
            form_values=form_values,
        ), status_code=400)

    user = crud.create_user(db, name[:120], email[:200], mobile[:20], hash_password(password))
    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/login")
def user_login_form(request: Request, db: Session = Depends(get_db)):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("user_login.html", ctx(
        request, db,
        active_nav="login",
        error=None,
    ))


@router.post("/login")
def user_login_submit(
    request: Request,
    identifier: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = crud.get_user_by_identifier(db, identifier)
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("user_login.html", ctx(
            request, db,
            active_nav="login",
            error="Invalid email/mobile or password.",
        ), status_code=400)

    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/logout")
def user_logout(request: Request):
    request.session.pop("user_id", None)
    return RedirectResponse(url="/", status_code=303)


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return templates.TemplateResponse("dashboard.html", ctx(
        request, db,
        active_nav="dashboard",
    ))
