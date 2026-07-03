# Bookshelf — System Architecture

## Overview

Bookshelf is a social book-tracking web application. Users maintain a personal shelf of books they have read, connect with friends, and browse each other's shelves. The stack is **Flask → Gunicorn → PostgreSQL**, deployed on a single Hetzner VM behind Nginx with HTTPS via Let's Encrypt.

---

## Infrastructure Layout

```mermaid
flowchart TD
    Internet(["🌐 Internet / Browser"])
    DDNS(["nbookshelf.ddns.net\nNo-IP DDNS"])

    subgraph VM["Hetzner Cloud VM"]
        direction TB
        Nginx["Nginx\nReverse Proxy + TLS termination"]
        Static["Static files /static/\nserved by Nginx, 7-day cache"]
        Gunicorn["Gunicorn\n2 workers · Unix socket"]
        Flask["Flask app.py"]
        Env[".env — Secrets & config"]
        Postgres[("PostgreSQL\nbk_db")]
        Logs["Logs\n/var/log/bookshelf/"]
    end

    GoogleOAuth(["Google OAuth 2.0\naccounts.google.com"])
    hCaptcha(["hCaptcha\napi.hcaptcha.com"])

    Internet --> DDNS --> Nginx
    Nginx -->|"GET /static/**"| Static
    Nginx -->|"all other requests"| Gunicorn
    Gunicorn --> Flask
    Env -. loaded at startup .-> Flask
    Flask --> Postgres
    Flask <-->|"OAuth exchange"| GoogleOAuth
    Flask <-->|"captcha verify"| hCaptcha
    Flask --> Logs
```

---

## Application Component Map

```mermaid
block-beta
  columns 4

  block:Auth["Auth Layer"]:2
    columns 2
    Signup["POST /signup\n(username+bcrypt)"]
    Login["POST /login\n(username+bcrypt)"]
    GoogleInit["GET /auth/google\n(OAuth init)"]
    GoogleCB["GET /auth/google/callback\n(OAuth exchange)"]
    Logout["POST /logout"]
  end

  block:Books["Book Routes"]:2
    columns 2
    Index["GET /\n(My Shelf)"]
    AddBook["POST /books/add"]
    EditBook["POST /books/:id/edit"]
    DeleteBook["POST /books/:id/delete"]
  end

  block:Social["Social Routes"]:2
    columns 2
    Friends["GET /friends\n(Friend Management)"]
    UserSearch["GET /users/search"]
    SendReq["POST /friends/request/:id"]
    AcceptReq["POST /friends/accept/:id"]
    DeclineReq["POST /friends/decline/:id"]
    RemoveFriend["POST /friends/remove/:id"]
  end

  block:Shelf["Shelf Browsing"]:2
    columns 2
    ViewShelf["GET /shelf/:user_id\n(Read-only, friends only)"]
  end

  block:Middleware["Cross-Cutting Concerns"]:4
    columns 4
    LoginDec["@login_required\ndecorator"]
    CtxProc["context_processor\npending_count badge"]
    CookieSec["Session Cookie\nHttpOnly + SameSite"]
    CSRF["State token\n(OAuth CSRF guard)"]
  end

  block:DB["PostgreSQL — bk_db"]:4
    columns 3
    Users["users\nid, username, password_hash,\nemail, google_id, created_at"]
    Bks["books\nid, user_id, title, author,\nyear, rating, added_at"]
    Friendships["friendships\nid, requester_id, addressee_id,\nstatus, created_at"]
  end
```

---

## Data Model (Entity-Relationship)

```mermaid
erDiagram
    users {
        serial      id            PK
        varchar50   username      UK
        varchar255  password_hash "NULL for Google-only"
        varchar255  email         UK "NULL until set"
        varchar255  google_id     UK "Google sub identifier"
        timestamptz created_at
    }

    books {
        serial      id        PK
        integer     user_id   FK
        varchar255  title
        varchar255  author
        integer     year
        numeric31   rating    "0.0 – 5.0, nullable"
        timestamptz added_at
    }

    friendships {
        serial      id           PK
        integer     requester_id FK
        integer     addressee_id FK
        varchar10   status       "pending | accepted"
        timestamptz created_at
    }

    users ||--o{ books        : "owns"
    users ||--o{ friendships  : "initiates (requester)"
    users ||--o{ friendships  : "receives (addressee)"
```

---

## Deployment Pipeline

```mermaid
flowchart LR
    Dev["Developer\nLocal Machine"] -->|git push origin main| GH["GitHub\nRepository"]
    Dev -->|"./deploy/deploy.sh\n(runs on VM directly)"| VM

    subgraph VM["Hetzner VM"]
        direction TB
        Pull["git fetch + reset --hard"] --> Pip["pip install -r requirements.txt"]
        Pip --> Daemon["systemctl daemon-reload"]
        Daemon --> Restart["systemctl restart bookshelf"]
        Restart --> Health["Health check\nsystemctl is-active"]
        Health --> NginxReload["nginx -t && systemctl reload nginx"]
    end

    GH -.->|code source| VM
```

---

## Process & Networking

```mermaid
flowchart TD
    Browser(["Browser"])
    LE(["Let's Encrypt / Certbot"])

    subgraph Nginx["Nginx — port 80 / 443"]
        TLS["TLS termination\nfullchain.pem + privkey.pem"]
        StaticServe["Serve /static/**\n7-day immutable cache"]
        ProxyPass["proxy_pass\nHTTP → Unix socket"]
    end

    subgraph Gunicorn["Gunicorn — /run/bookshelf/bookshelf.sock"]
        W1["Worker 1"]
        W2["Worker 2"]
    end

    Systemd["systemd\nbookshelf.service\nRestart=on-failure"]
    PG[("PostgreSQL\nlocalhost:5432")]

    LE -. "certificate renewal" .-> TLS
    Browser -->|"HTTPS :443"| TLS
    TLS --> StaticServe
    TLS --> ProxyPass
    ProxyPass --> W1
    ProxyPass --> W2
    Systemd -->|"manages"| Gunicorn
    W1 --> PG
    W2 --> PG
```
