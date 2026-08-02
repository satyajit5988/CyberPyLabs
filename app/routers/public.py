from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CATEGORIES, CATEGORY_LABELS
from .. import crud
from ..auth import get_optional_admin

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

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
        "current_year": datetime.now(timezone.utc).year,
        "categories": CATEGORIES,
        "category_labels": CATEGORY_LABELS,
    }
    base.update(extra)
    return base


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    latest = crud.list_published_posts(db, limit=5)
    return templates.TemplateResponse("index.html", ctx(
        request, db,
        active_nav="home",
        latest_posts=latest,
        category_descriptions=CATEGORY_DESCRIPTIONS,
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
