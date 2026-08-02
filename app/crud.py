import markdown as md
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .models import Post, Comment, ContactMessage
from .auth import slugify

MD_EXTENSIONS = ["fenced_code", "codehilite", "tables", "toc", "nl2br"]
MD_EXT_CONFIG = {"codehilite": {"guess_lang": False}}


def render_markdown(text: str) -> str:
    return md.markdown(text, extensions=MD_EXTENSIONS, extension_configs=MD_EXT_CONFIG)


def unique_slug(db: Session, title: str, ignore_post_id: int | None = None) -> str:
    base = slugify(title) or "post"
    slug = base
    counter = 2
    while True:
        q = db.query(Post).filter(Post.slug == slug)
        if ignore_post_id is not None:
            q = q.filter(Post.id != ignore_post_id)
        if not q.first():
            return slug
        slug = f"{base}-{counter}"
        counter += 1


def list_published_posts(db: Session, category: str | None = None, limit: int | None = None):
    q = db.query(Post).filter(Post.published.is_(True))
    if category:
        q = q.filter(Post.category == category)
    q = q.order_by(desc(Post.created_at))
    if limit:
        q = q.limit(limit)
    return q.all()


def list_all_posts(db: Session):
    return db.query(Post).order_by(desc(Post.created_at)).all()


def get_post_by_slug(db: Session, slug: str, published_only: bool = True):
    q = db.query(Post).filter(Post.slug == slug)
    if published_only:
        q = q.filter(Post.published.is_(True))
    return q.first()


def get_post_by_id(db: Session, post_id: int):
    return db.query(Post).filter(Post.id == post_id).first()


def create_post(db: Session, title, category, excerpt, content_md, published) -> Post:
    post = Post(
        title=title,
        slug=unique_slug(db, title),
        category=category,
        excerpt=excerpt,
        content_md=content_md,
        content_html=render_markdown(content_md),
        published=published,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def update_post(db: Session, post: Post, title, category, excerpt, content_md, published) -> Post:
    if title != post.title:
        post.slug = unique_slug(db, title, ignore_post_id=post.id)
    post.title = title
    post.category = category
    post.excerpt = excerpt
    post.content_md = content_md
    post.content_html = render_markdown(content_md)
    post.published = published
    db.commit()
    db.refresh(post)
    return post


def delete_post(db: Session, post: Post):
    db.delete(post)
    db.commit()


def add_comment(db: Session, post: Post, author_name: str, body: str) -> Comment:
    comment = Comment(post_id=post.id, author_name=author_name, body=body)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def add_contact_message(db: Session, name: str, email: str, subject: str, body: str) -> ContactMessage:
    message = ContactMessage(name=name, email=email, subject=subject, body=body)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def list_contact_messages(db: Session):
    return db.query(ContactMessage).order_by(ContactMessage.created_at.desc()).all()


def count_unread_messages(db: Session) -> int:
    return db.query(ContactMessage).filter(ContactMessage.is_read == False).count()  # noqa: E712


def get_contact_message_by_id(db: Session, message_id: int):
    return db.query(ContactMessage).filter(ContactMessage.id == message_id).first()


def set_message_read(db: Session, message: ContactMessage, is_read: bool) -> ContactMessage:
    message.is_read = is_read
    db.commit()
    db.refresh(message)
    return message


def delete_contact_message(db: Session, message: ContactMessage) -> None:
    db.delete(message)
    db.commit()
