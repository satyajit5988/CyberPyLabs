#!/usr/bin/env bash
#
# One-time setup for a fresh Ubuntu 24.04 VPS (e.g. a new DigitalOcean
# Droplet). Run this once, as root, via SSH:
#
#   ssh root@YOUR_SERVER_IP
#   curl -O https://raw.githubusercontent.com/YOUR_GITHUB_USER/CyberPyLabs/main/deploy/setup-server.sh
#   chmod +x setup-server.sh
#   ./setup-server.sh
#
# It installs Python, PostgreSQL, Nginx, Certbot, clones your repo,
# creates a dedicated non-root user to run the app, sets up the
# systemd service, configures the firewall, and prints the DNS record
# you need to add at your domain registrar.
#
# Safe to re-run - steps that are already done are skipped or just
# repeat harmlessly (apt install, systemctl enable, etc).

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root (or with sudo)." >&2
  exit 1
fi

echo "=== CyberPy Labs server setup ==="
read -rp "Git repo URL (e.g. https://github.com/satyajit5988/CyberPyLabs.git): " REPO_URL
read -rp "Your domain (e.g. cyberpylabs.com, no https://): " DOMAIN
read -rp "Postgres database name [cyberpylabs]: " DB_NAME
DB_NAME=${DB_NAME:-cyberpylabs}
read -rp "Postgres app username [cyberpylabs]: " DB_USER
DB_USER=${DB_USER:-cyberpylabs}
DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
SESSION_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
read -rp "Admin username for the site: " ADMIN_USERNAME
read -rsp "Admin password for the site: " ADMIN_PASSWORD
echo

echo "--- Installing packages ---"
apt-get update -y
apt-get install -y python3 python3-venv python3-pip postgresql postgresql-contrib \
  nginx certbot python3-certbot-nginx git ufw

echo "--- Creating app user ---"
id -u cyberpylabs &>/dev/null || useradd --system --create-home --shell /usr/sbin/nologin cyberpylabs

echo "--- Setting up PostgreSQL ---"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

echo "--- Cloning application ---"
if [ -d /opt/cyberpylabs/.git ]; then
  cd /opt/cyberpylabs && git pull
else
  git clone "$REPO_URL" /opt/cyberpylabs
fi
chown -R cyberpylabs:cyberpylabs /opt/cyberpylabs

echo "--- Python environment ---"
sudo -u cyberpylabs python3 -m venv /opt/cyberpylabs/venv
sudo -u cyberpylabs /opt/cyberpylabs/venv/bin/pip install --upgrade pip -q
sudo -u cyberpylabs /opt/cyberpylabs/venv/bin/pip install -r /opt/cyberpylabs/requirements.txt -q

echo "--- Writing /etc/cyberpylabs.env (root-only, holds secrets) ---"
cat > /etc/cyberpylabs.env <<EOF
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@localhost/${DB_NAME}
SESSION_SECRET=${SESSION_SECRET}
ADMIN_USERNAME=${ADMIN_USERNAME}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
EOF
chmod 600 /etc/cyberpylabs.env

echo "--- Installing systemd service ---"
cp /opt/cyberpylabs/deploy/cyberpylabs.service /etc/systemd/system/cyberpylabs.service
systemctl daemon-reload
systemctl enable cyberpylabs
systemctl restart cyberpylabs

echo "--- Configuring Nginx ---"
sed "s/YOUR_DOMAIN/${DOMAIN}/g" /opt/cyberpylabs/deploy/nginx.conf > /etc/nginx/sites-available/cyberpylabs
ln -sf /etc/nginx/sites-available/cyberpylabs /etc/nginx/sites-enabled/cyberpylabs
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "--- Configuring firewall ---"
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo ""
echo "=================================================================="
echo "Server setup complete."
echo ""
echo "NEXT STEPS:"
echo "1. At your domain registrar (GoDaddy), add an A record:"
echo "     ${DOMAIN}       -> $(curl -s ifconfig.me)"
echo "     www.${DOMAIN}   -> $(curl -s ifconfig.me)"
echo "   (DNS can take a few minutes to a few hours to propagate)"
echo ""
echo "2. Once DNS resolves to this server, run:"
echo "     sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"
echo "   This gets you free auto-renewing HTTPS."
echo ""
echo "3. Your site is already running at: http://$(curl -s ifconfig.me)"
echo "   (will move to https://${DOMAIN} once steps 1-2 are done)"
echo ""
echo "Database credentials and session secret were generated randomly"
echo "and saved to /etc/cyberpylabs.env (root-only). You don't need to"
echo "remember them, but back that file up somewhere safe."
echo "=================================================================="
