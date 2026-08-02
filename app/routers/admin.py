from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CATEGORIES, CATEGORY_LABELS, AdminUser
from .. import crud
from ..auth import verify_password, get_current_admin, get_optional_admin

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


def ctx(request: Request, db: Session, **extra):
    admin_user = get_optional_admin(request, db)
    base = {
        "request": request,
        "admin": admin_user,
        "current_year": datetime.now(timezone.utc).year,
        "categories": CATEGORIES,
        "category_labels": CATEGORY_LABELS,
        "unread_message_count": crud.count_unread_messages(db) if admin_user else 0,
    }
    base.update(extra)
    return base


@router.get("/login")
def login_form(request: Request, db: Session = Depends(get_db)):
    if request.session.get("admin_user_id"):
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    return templates.TemplateResponse("admin_login.html", ctx(request, db, active_nav="admin", error=None))


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(AdminUser).filter(AdminUser.username == username.strip()).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("admin_login.html", ctx(
            request, db, active_nav="admin", error="Invalid username or password."
        ), status_code=401)

    request.session["admin_user_id"] = user.id
    return RedirectResponse(url="/admin/dashboard", status_code=303)


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
        request, db, active_nav="admin", post=None, error=None
    ))


@router.post("/posts/new")
def new_post_submit(
    request: Request,
    title: str = Form(...),
    category: str = Form(...),
    excerpt: str = Form(""),
    content_md: str = Form(...),
    published: bool = Form(False),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    title = title.strip()
    content_md = content_md.strip()
    if not title or not content_md:
        return templates.TemplateResponse("admin_post_form.html", ctx(
            request, db, active_nav="admin", post=None, error="Title and content are required."
        ), status_code=400)

    post = crud.create_post(db, title, category, excerpt.strip(), content_md, published)
    return RedirectResponse(url="/admin/dashboard", status_code=303)


@router.get("/posts/{post_id}/edit")
def edit_post_form(post_id: int, request: Request, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    post = crud.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse("admin_post_form.html", ctx(
        request, db, active_nav="admin", post=post, error=None
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
            request, db, active_nav="admin", post=post, error="Title and content are required."
        ), status_code=400)

    crud.update_post(db, post, title, category, excerpt.strip(), content_md, published)
    return RedirectResponse(url="/admin/dashboard", status_code=303)


@router.post("/posts/{post_id}/delete")
def delete_post_submit(post_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    post = crud.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    crud.delete_post(db, post)
    return RedirectResponse(url="/admin/dashboard", status_code=303)
