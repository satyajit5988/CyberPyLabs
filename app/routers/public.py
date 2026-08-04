import os
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CATEGORIES, CATEGORY_LABELS, CATEGORY_SLUGS
from .. import crud
from ..auth import get_optional_admin, get_optional_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Cache-busting version for /static assets, so a fresh deploy is never masked
# by a browser (or CDN) holding onto a stale cached style.css.
try:
    _ASSET_VERSION = str(int(os.path.getmtime("app/static/css/style.css")))
except OSError:
    _ASSET_VERSION = "1"
templates.env.globals["asset_version"] = _ASSET_VERSION

CATEGORY_DESCRIPTIONS = {
    "python": "From beginner to advanced Python with automation, APIs and projects.",
    "cybersecurity": "OWASP, Linux Security, Threat Hunting, Vulnerability Management.",
    "networking": "TCP/IP, DNS, HTTP, VPNs, Firewalls and packet analysis.",
    "docker": "Containers, Images, Compose, Networking and Production Practices.",
    "kubernetes": "Pods, Deployments, Helm, Ingress, Monitoring and Troubleshooting.",
    "cloud": "Core cloud concepts, deployment patterns and managed services.",
    "automation": "Python, QA Automation, DevOps and Cybersecurity interview questions.",
    "linux": "Shell fundamentals, permissions, processes and system administration.",
    "testing": "Manual & automated testing, pytest, and QA best practices.",
    "interview": "Curated interview questions across Python, DevOps and Security.",
}


def ctx(request: Request, db: Session, **extra):
    """Shared template context: nav state, current admin, year, category data."""
    base = {
        "request": request,
        "admin": get_optional_admin(request, db),
        "user": get_optional_user(request, db),
        "current_year": datetime.now(timezone.utc).year,
        "categories": CATEGORIES,
        "category_labels": CATEGORY_LABELS,
    }
    base.update(extra)
    return base


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    latest = crud.list_published_posts(db, limit=5)
    categories_with_tracks = {slug for slug, _ in CATEGORIES if crud.category_has_track(db, slug)}
    return templates.TemplateResponse("index.html", ctx(
        request, db,
        active_nav="home",
        latest_posts=latest,
        category_descriptions=CATEGORY_DESCRIPTIONS,
        categories_with_tracks=categories_with_tracks,
    ))


@router.get("/learn/{category}")
def learn_category(category: str, db: Session = Depends(get_db)):
    if category not in CATEGORY_SLUGS:
        raise HTTPException(status_code=404, detail="Category not found")
    lessons = crud.get_track_posts(db, category)
    if not lessons:
        # No lesson-track content for this category yet - fall back to the
        # regular blog listing filtered to it, rather than a dead end.
        return RedirectResponse(url=f"/blog?category={category}", status_code=303)
    return RedirectResponse(url=f"/learn/{category}/{lessons[0].slug}", status_code=303)


@router.get("/learn/{category}/{slug}")
def learn_lesson(category: str, slug: str, request: Request, db: Session = Depends(get_db)):
    if category not in CATEGORY_SLUGS:
        raise HTTPException(status_code=404, detail="Category not found")
    lessons = crud.get_track_posts(db, category)
    post = next((p for p in lessons if p.slug == slug), None)
    if not post:
        raise HTTPException(status_code=404, detail="Lesson not found")

    current_user = get_optional_user(request, db)
    if current_user:
        crud.set_last_visited_post(db, current_user, post)

    grouped_lessons = {"beginner": [], "intermediate": [], "advanced": []}
    for lesson in lessons:
        grouped_lessons.setdefault(lesson.track_level, []).append(lesson)

    return templates.TemplateResponse("topic_lesson.html", ctx(
        request, db,
        active_nav=category,
        category=category,
        post=post,
        grouped_lessons=grouped_lessons,
    ))


@router.get("/blog")
def blog_list(request: Request, category: str | None = None, db: Session = Depends(get_db)):
    posts = crud.list_published_posts(db, category=category)
    heading = CATEGORY_LABELS.get(category, "All Posts") if category else "All Posts"
    active_nav = "interview" if category == "interview" else "blog"
    return templates.TemplateResponse("blog_list.html", ctx(
        request, db,
        active_nav=active_nav,
        posts=posts,
        selected_category=category,
        heading=heading,
    ))


@router.get("/post/{slug}")
def post_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    post = crud.get_post_by_slug(db, slug)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    current_user = get_optional_user(request, db)
    if current_user:
        crud.set_last_visited_post(db, current_user, post)
    return templates.TemplateResponse("post_detail.html", ctx(
        request, db,
        active_nav="blog",
        post=post,
        comment_error=None,
        comment_success=request.query_params.get("commented") == "1",
    ))


@router.get("/contact")
def contact(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("contact.html", ctx(
        request, db,
        active_nav="contact",
        form_error=None,
        form_values={},
        sent=request.query_params.get("sent") == "1",
    ))


@router.post("/contact")
def contact_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    subject: str = Form(""),
    body: str = Form(...),
    db: Session = Depends(get_db),
):
    name = name.strip()
    email = email.strip()
    subject = subject.strip()
    body = body.strip()

    if not name or not email or not body:
        return templates.TemplateResponse("contact.html", ctx(
            request, db,
            active_nav="contact",
            form_error="Name, email and message are required.",
            form_values={"name": name, "email": email, "subject": subject, "body": body},
            sent=False,
        ), status_code=400)

    crud.add_contact_message(db, name[:120], email[:200], subject[:200], body[:4000])
    return RedirectResponse(url="/contact?sent=1", status_code=303)


@router.post("/post/{slug}/comments")
def add_comment(
    slug: str,
    request: Request,
    author_name: str = Form(...),
    body: str = Form(...),
    db: Session = Depends(get_db),
):
    post = crud.get_post_by_slug(db, slug)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    author_name = author_name.strip()
    body = body.strip()
    if not author_name or not body:
        return templates.TemplateResponse("post_detail.html", ctx(
            request, db,
            active_nav="blog",
            post=post,
            comment_error="Name and comment can't be empty.",
            comment_success=False,
        ), status_code=400)

    crud.add_comment(db, post, author_name[:80], body[:2000])
    return RedirectResponse(url=f"/post/{slug}?commented=1", status_code=303)
