# CyberPy Labs

A full blog/tutorial site for Python, Cybersecurity, Networking, Docker,
Kubernetes, and related topics — built around your original landing page
design.

**Stack:** FastAPI + SQLAlchemy (SQLite) + Jinja2 + vanilla JS (no build step, no frontend framework).

## What's included

- Public site: homepage, blog listing with category filters, individual post
  pages, comments
- Admin panel: login, dashboard, create/edit/delete posts, Markdown editor
  with live preview, draft/publish toggle
- Posts are written in Markdown (with fenced code blocks + syntax
  highlighting) and rendered to HTML on save

## Project structure

```
app/
  main.py          FastAPI app + startup
  database.py      SQLite engine/session
  models.py        Post, Comment, AdminUser tables + category list
  auth.py          Password hashing, session auth, slug generation
  crud.py          All database queries + Markdown rendering
  seed.py          One-time script to create tables + your admin login
  routers/
    public.py      Home, blog, post detail, comments
    admin.py       Login, dashboard, post CRUD
  templates/       Jinja2 HTML templates
  static/css/      Shared stylesheet (extends your original mockup)
requirements.txt
```

## Running it locally

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Creates the database tables and prompts you to set an admin username/password
python -m app.seed

# Start the dev server
uvicorn app.main:app --reload
```

Visit:
- `http://127.0.0.1:8000/` — the site
- `http://127.0.0.1:8000/admin/login` — admin panel

## Adding categories

Categories live in one place: the `CATEGORIES` list in `app/models.py`.
Add or rename entries there and they'll automatically show up in the nav
cards, blog filter pills, and the admin post form's category dropdown.

## Before deploying

1. **Set a real session secret.** Set the `SESSION_SECRET` environment
   variable to a long random string (the code falls back to an insecure
   dev value otherwise):
   ```bash
   export SESSION_SECRET="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
   ```
2. **Move off SQLite if you expect concurrent writers** — set the
   `DATABASE_URL` environment variable to a Postgres connection string.
   No code changes needed.
3. **Serve over HTTPS** in production so session cookies aren't sent in
   plaintext, and consider setting `same_site="strict"` in
   `app/main.py` if you don't need cross-site cookie behavior.
4. **Run with a production ASGI setup**, e.g.:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
   ```
   (or behind Gunicorn with `uvicorn.workers.UvicornWorker`, fronted by
   Nginx/Caddy for TLS).
5. Common low-cost hosts that work well for this: Render, Railway,
   Fly.io, or a small VPS with a systemd service + Caddy for TLS.

## Notes on comments

Comments are open (no login required to post) with basic length limits.
If you get spam, the easiest next step is adding a honeypot field or a
CAPTCHA (e.g. hCaptcha) to the comment form — happy to add that if it
becomes a problem.
