#!/usr/bin/env bash
# deploy/setup_https.sh
#
# ONE-TIME script to enable HTTPS for nbookshelf.ddns.net using
# Let's Encrypt (via Certbot) and your existing Nginx config.
#
# Run this ON THE VM, after Nginx is already serving the site over plain HTTP:
#   scp deploy/setup_https.sh ubuntu@YOUR_VM_IP:~
#   ssh ubuntu@YOUR_VM_IP
#   chmod +x setup_https.sh
#   sudo bash setup_https.sh

set -euo pipefail

DOMAIN="nbookshelf.ddns.net"
ENV_FILE="/srv/bookshelf/.env"

# ── Read ADMIN_EMAIL from .env ────────────────────────────────────────────────
# Add this line to your .env on the VM (never commit it):
#   ADMIN_EMAIL=you@example.com
# The grep strips export/quotes/spaces; the script exits clearly if it's missing.
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found. Cannot read ADMIN_EMAIL."
    exit 1
fi

ADMIN_EMAIL=$(grep -E '^ADMIN_EMAIL=' "$ENV_FILE" \
    | head -n1 \
    | sed 's/^ADMIN_EMAIL=//' \
    | tr -d '"'"'"' ')

if [ -z "$ADMIN_EMAIL" ]; then
    echo "ERROR: ADMIN_EMAIL is not set in $ENV_FILE."
    echo "       Add this line to $ENV_FILE on the VM and re-run:"
    echo "         ADMIN_EMAIL=you@example.com"
    exit 1
fi

echo "    Using email: $ADMIN_EMAIL"

echo "==> [1/4] Confirming DNS resolves correctly"
RESOLVED_IP=$(dig +short "$DOMAIN" | tail -n1)
MY_IP=$(curl -4 -s ifconfig.me)
echo "    $DOMAIN resolves to: $RESOLVED_IP"
echo "    This VM's public IP: $MY_IP"
if [ "$RESOLVED_IP" != "$MY_IP" ]; then
    echo ""
    echo "    WARNING: DNS does not point to this VM yet."
    echo "    Let's Encrypt verification will fail until this matches."
    echo "    Check your DuckDNS/No-IP dashboard and try again."
    read -p "    Continue anyway? (y/N) " confirm
    [ "$confirm" = "y" ] || exit 1
fi

echo "==> [2/4] Installing Certbot"
apt-get update -qq
apt-get install -y -qq certbot python3-certbot-nginx

echo "==> [3/4] Requesting certificate and configuring Nginx"
# --nginx plugin edits your existing config automatically:
#   - adds a 443 server block with the cert paths filled in
#   - adds an HTTP -> HTTPS redirect on port 80
#   - reloads nginx for you
certbot --nginx \
    -d "$DOMAIN" \
    --non-interactive \
    --agree-tos \
    --redirect \
    -m "$ADMIN_EMAIL"

echo "==> [4/4] Verifying auto-renewal is scheduled"
systemctl list-timers | grep certbot || echo "    (certbot.timer should appear above; if not, check: systemctl status certbot.timer)"

echo ""
echo "══════════════════════════════════════════════════════"
echo "  HTTPS is live: https://$DOMAIN"
echo ""
echo "  Certificates auto-renew via systemd timer — nothing"
echo "  further to do. Test renewal with:"
echo "     sudo certbot renew --dry-run"
echo ""
echo "  Next: set FORCE_HTTPS=true in /srv/bookshelf/.env"
echo "  then: sudo systemctl restart bookshelf"
echo "══════════════════════════════════════════════════════"
