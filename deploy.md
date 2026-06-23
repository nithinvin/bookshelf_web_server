# Bookshelf Service — Deployment Guide

Stack: **Ubuntu 24.04 → Nginx → Unix socket → Gunicorn → Flask → PostgreSQL**

---

## Directory layout on the VM

```
/srv/bookshelf/          ← git repo lives here
    app.py
    schema.sql
    requirements.txt
    .env                 ← secrets (never committed)
    venv/                ← Python virtualenv
    static/
    templates/
    deploy/
        bookshelf.service
        nginx_bookshelf.conf
        server_setup.sh
        deploy.sh

/run/bookshelf/
    bookshelf.sock       ← Gunicorn Unix socket (systemd creates this dir)

/var/log/bookshelf/
    access.log
    error.log
```

---

## Step 1 — First-time VM setup (run once)

SSH into your VM and run the setup script:

```bash
# From your local machine
scp deploy/server_setup.sh ubuntu@YOUR_VM_IP:~
ssh ubuntu@YOUR_VM_IP
chmod +x server_setup.sh
sudo bash server_setup.sh
```

This installs Python, PostgreSQL, Nginx, clones your repo, creates the
`bookshelf` system user, installs the systemd service, and links the Nginx config.

---

## Step 2 — Create the database

```bash
ssh ubuntu@YOUR_VM_IP

# Create DB user and database
sudo -u postgres psql -c "CREATE USER bookshelf_user WITH PASSWORD 'your_strong_password';"
sudo -u postgres psql -c "CREATE DATABASE bookshelf_db OWNER bookshelf_user;"

# Run the schema
psql -U bookshelf_user -d bookshelf_db -h localhost -f /srv/bookshelf/schema.sql
```

---

## Step 3 — Create .env on the VM

```bash
ssh ubuntu@YOUR_VM_IP
sudo cp /srv/bookshelf/.env.example /srv/bookshelf/.env
sudo nano /srv/bookshelf/.env
```

Fill in every value:

```
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=<generate with: python3 -c "import secrets; print(secrets.token_hex(32))">
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bookshelf_db
DB_USER=bookshelf_user
DB_PASSWORD=your_strong_password
```

Lock down the file so only root can read it:

```bash
sudo chown root:bookshelf /srv/bookshelf/.env
sudo chmod 640 /srv/bookshelf/.env
```

---

## Step 4 — Edit deploy/nginx_bookshelf.conf

Replace `YOUR_DOMAIN_OR_IP` with your actual VM IP or domain name, then commit
and push, or edit directly on the VM:

```bash
sudo nano /etc/nginx/sites-available/bookshelf
sudo nginx -t && sudo systemctl reload nginx
```

---

## Step 5 — Edit deploy/deploy.sh

Open `deploy/deploy.sh` and set:

```bash
VM_USER="ubuntu"         # your SSH user
VM_HOST="YOUR_VM_IP"     # VM IP or domain
```

---

## Step 6 — Start the service

```bash
ssh ubuntu@YOUR_VM_IP
sudo systemctl start bookshelf
sudo systemctl status bookshelf
```

You should see `Active: active (running)`.

Visit `http://YOUR_VM_IP` — you should see the Bookshelf login page.

---

## Deploying updates (every time)

```bash
# 1. Make your changes locally
git add .
git commit -m "your message"
git push origin main

# 2. Deploy to the VM
./deploy/deploy.sh
```

The script SSHes in, pulls the latest code, updates pip packages if
`requirements.txt` changed, and restarts Gunicorn. Takes about 5–10 seconds.

---

## Useful commands on the VM

```bash
# Live service logs
journalctl -u bookshelf -f

# Last 50 log lines
journalctl -u bookshelf -n 50 --no-pager

# Restart manually
sudo systemctl restart bookshelf

# Check Nginx
sudo nginx -t
sudo systemctl status nginx

# Tail app logs
tail -f /var/log/bookshelf/access.log
tail -f /var/log/bookshelf/error.log
```

---

## Enabling HTTPS (nbookshelf.ddns.net)

You already have a free DDNS hostname pointing at your VM's IP:
`nbookshelf.ddns.net`. Let's Encrypt can issue a real, trusted certificate
for this because it's a proper hostname (not a bare IP).

### Step 1 — Push the updated Nginx config

`deploy/nginx_bookshelf.conf` now has `server_name nbookshelf.ddns.net;`
instead of the placeholder. Deploy it:

```bash
git add deploy/nginx_bookshelf.conf app.py .env.example
git commit -m "Configure domain for HTTPS"
git push origin main
./deploy/deploy.sh
```

Then on the VM, re-link the config (only needed if you edited it manually
rather than through deploy.sh):

```bash
ssh ubuntu@YOUR_VM_IP
sudo cp /srv/bookshelf/deploy/nginx_bookshelf.conf /etc/nginx/sites-available/bookshelf
sudo nginx -t && sudo systemctl reload nginx
```

Confirm the site is reachable over plain HTTP first:
`http://nbookshelf.ddns.net` — this must work before Certbot can verify
domain ownership.

### Step 2 — Run the HTTPS setup script

```bash
scp deploy/setup_https.sh ubuntu@YOUR_VM_IP:~
ssh ubuntu@YOUR_VM_IP
chmod +x setup_https.sh
sudo bash setup_https.sh
```

Before running, open the script and replace `your-email@example.com` with
a real email — Let's Encrypt uses it only to warn you if a renewal ever fails.

This script:
1. Confirms `nbookshelf.ddns.net` actually resolves to this VM's IP
2. Installs Certbot
3. Requests the certificate and lets Certbot edit your Nginx config
   automatically (adds the 443 block, redirects HTTP → HTTPS)
4. Confirms the auto-renewal timer is active

### Step 3 — Turn on secure cookies

Once `https://nbookshelf.ddns.net` loads with a padlock and no warnings:

```bash
ssh ubuntu@YOUR_VM_IP
sudo nano /srv/bookshelf/.env
# change: FORCE_HTTPS=false  →  FORCE_HTTPS=true
sudo systemctl restart bookshelf
```

This makes Flask's session cookie HTTPS-only, so login sessions can never
leak over a plain-HTTP connection.

### Step 4 — Verify renewal works

Certificates from Let's Encrypt expire every 90 days but renew automatically
via a systemd timer Certbot installs. Confirm it works without waiting:

```bash
sudo certbot renew --dry-run
```

If that succeeds, you're done — nothing else to maintain.

### A note on DuckDNS IP changes

If your VM's IP ever changes (it generally won't on Hetzner unless you
explicitly request a new one), update the DuckDNS record at duckdns.org,
then re-run `sudo certbot renew` to make sure the cert still matches.

---

## Firewall (ufw)

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

`Nginx Full` opens both port 80 (HTTP, needed for the redirect and for
Certbot's renewal checks) and port 443 (HTTPS). Port 8010 does **not**
need to be open — Nginx handles all incoming traffic and proxies
internally to the Gunicorn Unix socket.
