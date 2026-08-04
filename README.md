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

## Fastest way to see it live: Render (free, no local setup)

If you just want a public URL to click around and test — skipping your
local Python/venv setup entirely — Render's free tier works well for this.

1. **Push this project to a GitHub repo** (public or private — Render
   supports both once you connect your account).
2. Go to [render.com](https://render.com) and sign up (no credit card
   needed for the free tier).
3. **New +** → **Web Service** → connect the GitHub repo.
4. Configure:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance type:** Free
5. Under **Environment**, add these variables:
   | Key | Value |
   |---|---|
   | `SESSION_SECRET` | any long random string |
   | `ADMIN_USERNAME` | your chosen admin username |
   | `ADMIN_PASSWORD` | your chosen admin password |

   (`ADMIN_USERNAME`/`ADMIN_PASSWORD` are read once on first boot to create
   your admin login automatically — there's no shell access on the free
   tier to run `python -m app.seed` interactively.)
6. Click **Deploy**. You'll get a live `https://your-app.onrender.com` URL
   in a few minutes.

**Two free-tier things worth knowing:**
- The service **spins down after 15 minutes of inactivity** and takes
  ~30–60 seconds to wake back up on the next request — normal for
  testing, not something you'd want for a real audience.
- The filesystem is **ephemeral**: any posts/comments you add through
  the SQLite database are wiped whenever the service restarts, redeploys,
  or spins down from inactivity. Fine for a quick look at the UI; if you
  want data to actually stick around while testing, add a free Render
  Postgres instance and set the `DATABASE_URL` env var it gives you —
  the app already reads that automatically, no code changes needed.

## Self-hosted deployment (DigitalOcean + your own domain + auto-deploy)

Everything needed for this lives in `deploy/` and `.github/workflows/deploy.yml`.
One-time setup, then every `git push` to `main` redeploys automatically.

### 1. Create the server

- Sign up at [digitalocean.com](https://digitalocean.com), create a Droplet:
  Ubuntu 24.04, Basic plan, $6/mo (1GB RAM) is enough for this app.
- Note the Droplet's IP address.

### 2. Run the one-time setup script

SSH in as root and run the setup script — it installs Python, PostgreSQL,
Nginx, Certbot, clones this repo, and starts the app:

```bash
ssh root@YOUR_SERVER_IP
curl -O https://raw.githubusercontent.com/satyajit5988/CyberPyLabs/main/deploy/setup-server.sh
chmod +x setup-server.sh
./setup-server.sh
```

It'll prompt for your repo URL, domain name, and admin username/password.
Database credentials and the session secret are generated randomly for you.
At the end it prints your server's IP and the DNS records to add next.

### 3. Point your domain at the server

At your registrar (GoDaddy or similar), add:
- An **A record** for `@` (root domain) → your server's IP
- An **A record** for `www` → your server's IP

DNS propagation can take a few minutes to a few hours.

### 4. Get HTTPS

Once DNS resolves to your server:

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Free, auto-renewing certificate from Let's Encrypt. Your site is now live at
`https://yourdomain.com`.

### 5. Set up auto-deploy on push

Generate a dedicated SSH key pair for GitHub Actions to use (don't reuse your
personal key):

```bash
ssh-keygen -t ed25519 -f deploy_key -N "" -C "github-actions-deploy"
```

Add the **public** key (`deploy_key.pub`) to the server:

```bash
ssh-copy-id -i deploy_key.pub root@YOUR_SERVER_IP
```

In your GitHub repo → **Settings → Secrets and variables → Actions**, add:

| Secret name | Value |
|---|---|
| `SERVER_HOST` | Your server's IP address |
| `SERVER_USER` | `root` |
| `SERVER_SSH_KEY` | The **private** key content (`cat deploy_key`) |

That's it — every push to `main` now runs `deploy/deploy.sh` on the server
(pulls latest code, installs any new dependencies, restarts the app). You
can also trigger a redeploy manually from the repo's **Actions** tab without
pushing anything.

### Managing the live app

```bash
ssh root@YOUR_SERVER_IP
systemctl status cyberpylabs      # is it running?
journalctl -u cyberpylabs -f      # live logs
systemctl restart cyberpylabs     # manual restart
```

Secrets (`DATABASE_URL`, `SESSION_SECRET`, admin credentials) live in
`/etc/cyberpylabs.env` on the server, root-only readable, never in git.

## Notes on comments

Comments are open (no login required to post) with basic length limits.
If you get spam, the easiest next step is adding a honeypot field or a
CAPTCHA (e.g. hCaptcha) to the comment form — happy to add that if it
becomes a problem.
