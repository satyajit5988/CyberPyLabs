import os
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CATEGORIES, CATEGORY_LABELS, TRACK_LEVELS
from .. import crud
from ..auth import get_current_admin, get_optional_admin, get_optional_user

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")

try:
    _ASSET_VERSION = str(int(os.path.getmtime("app/static/css/style.css")))
except OSError:
    _ASSET_VERSION = "1"
templates.env.globals["asset_version"] = _ASSET_VERSION


def ctx(request: Request, db: Session, **extra):
    admin_user = get_optional_admin(request, db)
    base = {
        "request": request,
        "admin": admin_user,
        "user": get_optional_user(request, db),
        "current_year": datetime.now(timezone.utc).year,
        "categories": CATEGORIES,
        "category_labels": CATEGORY_LABELS,
        "unread_message_count": crud.count_unread_messages(db) if admin_user else 0,
    }
    base.update(extra)
    return base


@router.get("/login")
def login_form(request: Request):
    # Login is now unified at /login for both admin and regular users.
    return RedirectResponse(url="/login", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    posts = crud.list_all_posts(db)
    return templates.TemplateResponse("admin_dashboard.html", ctx(
        request, db, active_nav="admin", posts=posts
    ))


@router.get("/messages")
def messages(request: Request, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    msgs = crud.list_contact_messages(db)
    return templates.TemplateResponse("admin_messages.html", ctx(
        request, db, active_nav="messages", messages=msgs
    ))


@router.post("/messages/{message_id}/read")
def mark_message_read(message_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    message = crud.get_contact_message_by_id(db, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    crud.set_message_read(db, message, not message.is_read)
    return RedirectResponse(url="/admin/messages", status_code=303)


@router.post("/messages/{message_id}/delete")
def delete_message(message_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    message = crud.get_contact_message_by_id(db, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    crud.delete_contact_message(db, message)
    return RedirectResponse(url="/admin/messages", status_code=303)


@router.get("/posts/new")
def new_post_form(request: Request, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    return templates.TemplateResponse("admin_post_form.html", ctx(
        request, db, active_nav="admin", post=None, error=None, track_levels=TRACK_LEVELS
    ))


@router.post("/posts/new")
def new_post_submit(
    request: Request,
    title: str = Form(...),
    category: str = Form(...),
    excerpt: str = Form(""),
    content_md: str = Form(...),
    published: bool = Form(False),
    track_level: str = Form(""),
    track_order: int = Form(0),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    title = title.strip()
    content_md = content_md.strip()
    if not title or not content_md:
        return templates.TemplateResponse("admin_post_form.html", ctx(
            request, db, active_nav="admin", post=None, error="Title and content are required.",
            track_levels=TRACK_LEVELS,
        ), status_code=400)

    post = crud.create_post(db, title, category, excerpt.strip(), content_md, published,
                             track_level=track_level.strip(), track_order=track_order)
    return RedirectResponse(url="/admin/dashboard", status_code=303)


@router.get("/posts/{post_id}/edit")
def edit_post_form(post_id: int, request: Request, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    post = crud.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse("admin_post_form.html", ctx(
        request, db, active_nav="admin", post=post, error=None, track_levels=TRACK_LEVELS
    ))


@router.post("/posts/{post_id}/edit")
def edit_post_submit(
    post_id: int,
    request: Request,
    title: str = Form(...),
    category: str = Form(...),
    excerpt: str = Form(""),
    content_md: str = Form(...),
    published: bool = Form(False),
    track_level: str = Form(""),
    track_order: int = Form(0),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    post = crud.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    title = title.strip()
    content_md = content_md.strip()
    if not title or not content_md:
        return templates.TemplateResponse("admin_post_form.html", ctx(
            request, db, active_nav="admin", post=post, error="Title and content are required.",
            track_levels=TRACK_LEVELS,
        ), status_code=400)

    crud.update_post(db, post, title, category, excerpt.strip(), content_md, published,
                      track_level=track_level.strip(), track_order=track_order)
    return RedirectResponse(url="/admin/dashboard", status_code=303)


@router.post("/posts/{post_id}/delete")
def delete_post_submit(post_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    post = crud.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    crud.delete_post(db, post)
    return RedirectResponse(url="/admin/dashboard", status_code=303)
