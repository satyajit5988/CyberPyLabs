import markdown as md
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .models import Post, Comment, ContactMessage, User
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


_TRACK_LEVEL_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}


def get_track_posts(db: Session, category: str):
    """
    All published posts in a category that are part of a learning track
    (track_level is set), ordered for sidebar display: level group first
    (beginner -> intermediate -> advanced), then track_order within a level.
    """
    posts = (
        db.query(Post)
        .filter(Post.published.is_(True))
        .filter(Post.category == category)
        .filter(Post.track_level.isnot(None))
        .order_by(Post.track_order)
        .all()
    )
    posts.sort(key=lambda p: (_TRACK_LEVEL_ORDER.get(p.track_level, 99), p.track_order))
    return posts


def category_has_track(db: Session, category: str) -> bool:
    return (
        db.query(Post)
        .filter(Post.published.is_(True))
        .filter(Post.category == category)
        .filter(Post.track_level.isnot(None))
        .first()
        is not None
    )


def create_post(db: Session, title, category, excerpt, content_md, published,
                 track_level=None, track_order=0) -> Post:
    post = Post(
        title=title,
        slug=unique_slug(db, title),
        category=category,
        excerpt=excerpt,
        content_md=content_md,
        content_html=render_markdown(content_md),
        published=published,
        track_level=track_level or None,
        track_order=track_order or 0,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def update_post(db: Session, post: Post, title, category, excerpt, content_md, published,
                 track_level=None, track_order=0) -> Post:
    if title != post.title:
        post.slug = unique_slug(db, title, ignore_post_id=post.id)
    post.title = title
    post.category = category
    post.excerpt = excerpt
    post.content_md = content_md
    post.content_html = render_markdown(content_md)
    post.published = published
    post.track_level = track_level or None
    post.track_order = track_order or 0
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


def get_user_by_identifier(db: Session, identifier: str):
    """Look up a user by email (case-insensitive) or mobile number."""
    identifier = identifier.strip()
    return db.query(User).filter(
        (User.email == identifier.lower()) | (User.mobile == identifier)
    ).first()


def create_user(db: Session, name: str, email: str | None, mobile: str | None, password_hash: str) -> User:
    user = User(name=name, email=email or None, mobile=mobile or None, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_last_visited_post(db: Session, user: User, post: Post) -> None:
    if user.last_visited_post_id == post.id:
        return
    user.last_visited_post_id = post.id
    db.commit()
