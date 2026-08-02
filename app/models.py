from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utcnow)


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(220), unique=True, nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    excerpt = Column(String(300), nullable=True)
    content_md = Column(Text, nullable=False)       # raw markdown, as authored
    content_html = Column(Text, nullable=False)      # rendered HTML, cached at save time
    published = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    comments = relationship(
        "Comment", back_populates="post", cascade="all, delete-orphan",
        order_by="Comment.created_at"
    )


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    author_name = Column(String(80), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    post = relationship("Post", back_populates="comments")


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(200), nullable=False)
    subject = Column(String(200), nullable=True)
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow)


# Fixed set of categories shown across the site — keeps nav/cards/admin dropdown in sync.
CATEGORIES = [
    ("python", "🐍 Python"),
    ("cybersecurity", "🔐 Cybersecurity"),
    ("networking", "🌐 Networking"),
    ("docker", "🐳 Docker"),
    ("kubernetes", "☸ Kubernetes"),
    ("cloud", "☁️ Cloud"),
    ("automation", "💼 Automation"),
    ("linux", "🐧 Linux"),
    ("testing", "🧪 Testing"),
    ("interview", "🎯 Interview Prep"),
]
CATEGORY_SLUGS = {slug for slug, _ in CATEGORIES}
CATEGORY_LABELS = dict(CATEGORIES)
