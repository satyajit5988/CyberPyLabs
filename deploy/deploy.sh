#!/usr/bin/env bash
#
# Runs ON THE SERVER on every push to main (triggered via SSH by the
# GitHub Actions workflow at .github/workflows/deploy.yml). Not meant
# to be run manually, though it's safe to.

set -euo pipefail

cd /opt/cyberpylabs

echo "--- Pulling latest code ---"
sudo -u cyberpylabs git fetch origin
sudo -u cyberpylabs git reset --hard origin/main

echo "--- Installing any new dependencies ---"
sudo -u cyberpylabs /opt/cyberpylabs/venv/bin/pip install -r requirements.txt -q

echo "--- Restarting app ---"
systemctl restart cyberpylabs

echo "--- Done. Recent logs: ---"
journalctl -u cyberpylabs -n 20 --no-pager
