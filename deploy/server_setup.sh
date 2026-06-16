#!/usr/bin/env bash
# deploy/server_setup.sh
#
# ONE-TIME setup script. Run this once on a fresh Ubuntu 24.04 VM.
# After this, use deploy.sh for every subsequent code push.
#
# Usage (from your local machine):
#   ssh user@YOUR_VM_IP "bash -s" < deploy/server_setup.sh
#
# Or copy it to the VM and run directly:
#   scp deploy/server_setup.sh user@YOUR_VM_IP:~
#   ssh user@YOUR_VM_IP
#   chmod +x server_setup.sh && sudo bash server_setup.sh

set -euo pipefail

# ── CONFIG — edit these before running ───────────────────────────────────────
REPO_URL="https://github.com/YOUR_USERNAME/YOUR_REPO.git"  # your GitHub repo
REPO_BRANCH="main"
APP_DIR="/srv/bookshelf"
APP_USER="bookshelf"
LOG_DIR="/var/log/bookshelf"
# ─────────────────────────────────────────────────────────────────────────────

echo "==> [1/8] Updating system packages"
apt-get update -qq && apt-get upgrade -y -qq

echo "==> [2/8] Installing dependencies"
apt-get install -y -qq \
    python3 python3-pip python3-venv \
    postgresql postgresql-contrib \
    nginx \
    git \
    curl

echo "==> [3/8] Creating system user: $APP_USER"
if ! id "$APP_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$APP_USER"
fi

echo "==> [4/8] Cloning repo to $APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
    echo "    Repo already exists, skipping clone."
else
    git clone --branch "$REPO_BRANCH" "$REPO_URL" "$APP_DIR"
fi
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

echo "==> [5/8] Creating Python virtual environment and installing packages"
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "==> [6/8] Creating log directory"
mkdir -p "$LOG_DIR"
chown "$APP_USER":"$APP_USER" "$LOG_DIR"

echo "==> [7/8] Installing systemd service"
cp "$APP_DIR/deploy/bookshelf.service" /etc/systemd/system/bookshelf.service
systemctl daemon-reload
systemctl enable bookshelf
# (Don't start yet — .env must be created first)

echo "==> [8/8] Installing Nginx config"
cp "$APP_DIR/deploy/nginx_bookshelf.conf" /etc/nginx/sites-available/bookshelf
ln -sf /etc/nginx/sites-available/bookshelf /etc/nginx/sites-enabled/bookshelf
# Remove the default Nginx site if still enabled
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ""
echo "══════════════════════════════════════════════════════"
echo "  Setup complete. Before starting the service:"
echo ""
echo "  1. Create /srv/bookshelf/.env (copy from .env.example)"
echo "     and fill in your real DB credentials and SECRET_KEY."
echo ""
echo "  2. Set up the database:"
echo "     sudo -u postgres psql -c \"CREATE USER bookshelf_user WITH PASSWORD 'yourpassword';\""
echo "     sudo -u postgres psql -c \"CREATE DATABASE bookshelf_db OWNER bookshelf_user;\""
echo "     psql -U bookshelf_user -d bookshelf_db -f /srv/bookshelf/schema.sql"
echo ""
echo "  3. Start the service:"
echo "     sudo systemctl start bookshelf"
echo "     sudo systemctl status bookshelf"
echo "══════════════════════════════════════════════════════"
