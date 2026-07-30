"""
Run once to create the database tables and your first admin login:

    python -m app.seed

It will prompt for a username and password interactively so the
password is never typed into shell history or hardcoded in a file.
"""
import getpass
from .database import Base, engine, SessionLocal
from .models import AdminUser
from .auth import hash_password


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(AdminUser).count() > 0:
            print("An admin user already exists — skipping creation.")
            return
        print("Create your admin login for CyberPy Labs:")
        username = input("Username: ").strip()
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords did not match. Run again to retry.")
            return
        if len(password) < 8:
            print("Password should be at least 8 characters. Run again to retry.")
            return
        admin = AdminUser(username=username, password_hash=hash_password(password))
        db.add(admin)
        db.commit()
        print(f"Admin user '{username}' created. You can now log in at /admin/login")
    finally:
        db.close()


if __name__ == "__main__":
    main()
