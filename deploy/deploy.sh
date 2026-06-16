#!/usr/bin/env bash
# deploy/deploy.sh
#
# Run from your LOCAL machine (inside the repo) after every git push.
# Pulls latest code on the VM, updates dependencies, and restarts the service.
#
# Usage:
#   chmod +x deploy/deploy.sh       # one-time
#   ./deploy/deploy.sh              # every deployment
#
# Prerequisites on your local machine:
#   - SSH key already added to the VM (so no password prompt)
#   - git push already done before running this

set -euo pipefail

# ── CONFIG — edit these ───────────────────────────────────────────────────────
VM_USER="ubuntu"                # your SSH user on the VM
VM_HOST="YOUR_VM_IP"            # VM IP or domain
APP_DIR="/srv/bookshelf"
BRANCH="main"
SERVICE="bookshelf"
# ─────────────────────────────────────────────────────────────────────────────

echo "==> Deploying branch '$BRANCH' to $VM_USER@$VM_HOST"

ssh "$VM_USER@$VM_HOST" bash << REMOTE
set -euo pipefail

echo "--> Pulling latest code"
cd "$APP_DIR"
sudo git fetch origin "$BRANCH"
sudo git reset --hard "origin/$BRANCH"
sudo chown -R "$SERVICE":"$SERVICE" "$APP_DIR"

echo "--> Installing/updating Python dependencies"
sudo "$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
sudo "$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "--> Reloading systemd and restarting service"
sudo systemctl daemon-reload
sudo systemctl restart "$SERVICE"

echo "--> Checking service health"
sleep 2
sudo systemctl is-active --quiet "$SERVICE" \
    && echo "    ✓ Service is running" \
    || { echo "    ✗ Service failed to start — check logs:"; sudo journalctl -u "$SERVICE" -n 30 --no-pager; exit 1; }

echo "--> Reloading Nginx (picks up any config changes)"
sudo nginx -t && sudo systemctl reload nginx

REMOTE

echo ""
echo "✓ Deployment complete."
echo "  Logs : ssh $VM_USER@$VM_HOST 'journalctl -u $SERVICE -f'"
echo "  App  : http://$VM_HOST"
