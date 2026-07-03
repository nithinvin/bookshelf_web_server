# Bookshelf — System Architecture

## Overview

Bookshelf is a social book-tracking web application. Users maintain a personal shelf of books they have read, connect with friends, and browse each other's shelves. The stack is **Flask → Gunicorn → PostgreSQL**, deployed on a single Hetzner VM behind Nginx with HTTPS via Let's Encrypt.

---

## Infrastructure Layout

```mermaid
block-beta
  columns 3

  Internet(["Internet / Browser"]):::ext
  space
  DDNS(["nbookshelf.ddns.net\n(No-IP DDNS)"]):::ext

  space:3

  block:VM["Hetzner Cloud VM"]:3
    columns 3
    Nginx["Nginx\n(Reverse Proxy + TLS)"]:::infra
    space
    Static["Static Files\n/static/ (served by Nginx)"]:::infra

    space:3

    Gunicorn["Gunicorn\n(2 workers, Unix socket)"]:::app
    space
    Env[".env\n(Secrets)"]:::cfg

    space:3

    Flask["Flask Application\napp.py"]:::app
    space
    Venv["Python venv\n/srv/bookshelf/venv"]:::cfg

    space:3

    Postgres["PostgreSQL\nbk_db"]:::db
    space
    Logs["Log Files\n/var/log/bookshelf/"]:::cfg
  end

  space:3

  GoogleOAuth(["Google OAuth 2.0\naccounts.google.com"]):::ext
  space
  hCaptcha(["hCaptcha\napi.hcaptcha.com"]):::ext

  Internet --> DDNS
  DDNS --> Nginx
  Nginx --> Gunicorn
  Nginx --> Static
  Gunicorn --> Flask
  Flask --> Postgres
  Flask --> GoogleOAuth
  Flask --> hCaptcha

  classDef ext fill:#dbeafe,stroke:#3b82f6,color:#1e40af
  classDef infra fill:#fef9c3,stroke:#ca8a04,color:#713f12
  classDef app fill:#dcfce7,stroke:#16a34a,color:#14532d
  classDef db fill:#fce7f3,stroke:#db2777,color:#831843
  classDef cfg fill:#f3f4f6,stroke:#6b7280,color:#374151
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
block-beta
  columns 3

  Client(["Browser"]):::ext
  space
  LetsEncrypt(["Let's Encrypt\nCertbot"]):::ext

  space:3

  block:NginxBlock["Nginx (port 80 / 443)"]:3
    columns 3
    TLS["TLS Termination\n(fullchain + privkey)"]
    StaticServe["Static Files\n7-day cache"]
    ProxyPass["proxy_pass to\nUnix socket"]
  end

  space:3

  block:GunicornBlock["Gunicorn (Unix socket: /run/bookshelf/bookshelf.sock)"]:3
    columns 3
    W1["Worker 1"]
    W2["Worker 2"]
    Systemd["systemd unit\nbookshelf.service"]
  end

  space:3

  PG["PostgreSQL\nlocalhost:5432"]:::db

  Client -->|HTTPS 443| TLS
  LetsEncrypt --> TLS
  TLS --> ProxyPass
  ProxyPass --> W1
  ProxyPass --> W2
  W1 --> PG
  W2 --> PG

  classDef ext fill:#dbeafe,stroke:#3b82f6,color:#1e40af
  classDef db fill:#fce7f3,stroke:#db2777,color:#831843
```
