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

## Adding HTTPS with Let's Encrypt (optional but recommended)

```bash
ssh ubuntu@YOUR_VM_IP
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com
```

Certbot edits the Nginx config automatically and sets up auto-renewal.

---

## Firewall (ufw)

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

Port 8010 does **not** need to be open anymore — Nginx handles all incoming
traffic and proxies internally to the Gunicorn Unix socket.
