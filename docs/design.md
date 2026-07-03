# Bookshelf — Design Reference

## 1. Frontend Layer

### 1.1 Template Inheritance

All pages extend `base.html` which owns the sticky header, flash messages, footer, and shared script tags.

```mermaid
flowchart TD
    base["base.html\n─────────────\n• Sticky header (nav + badge)\n• Flash message container\n• Footer\n• main.js + block scripts"]

    base --> index["index.html\nUser's own shelf\nbook-grid + controls bar\n+ list.js"]
    base --> shelf["shelf_view.html\nFriend's shelf\n(read-only, no edit/delete)\n+ list.js"]
    base --> form["form.html\nAdd / Edit book\n(dual-mode, shared)\n+ form.js"]
    base --> friends["friends.html\nFriends management\n(incoming / accepted / outgoing)"]
    base --> usersearch["user_search.html\nGET-based username search\nrelationship status per result"]
    base --> login["login.html\nUsername+password\n+ Google OAuth button\n+ auth.js"]
    base --> signup["signup.html\nUsername+password + hCaptcha\n+ Google OAuth button\n+ auth.js"]
```

### 1.2 JavaScript Responsibilities per Page

| Script | Pages loaded on | Responsibility |
|--------|----------------|----------------|
| `main.js` | All pages (via `base.html`) | Auto-dismiss flash messages after 4 s; `confirmDelete()` dialog for book removal |
| `list.js` | `index.html`, `shelf_view.html` | Client-side live search (debounced 180 ms), min-rating filter, sort by title / author / year / rating — all operating on `data-*` attributes embedded in each `.book-card` |
| `auth.js` | `login.html`, `signup.html` | Inline field validation on blur/input; show/hide password toggle; password strength meter (0–4 score) on signup |
| `form.js` | `form.html` | Field validation (title, author, year, rating), live character counter for title (255 max), live star-fill preview as rating is typed |

### 1.3 CSS Design Tokens

```mermaid
flowchart LR
    subgraph Palette["style.css — custom properties"]
        direction TB
        cream["--cream / --cream-dark\nPage background"]
        ink["--ink / --ink-mid / --ink-light\nText hierarchy"]
        rust["--rust / --rust-light / --rust-pale\nPrimary action + accents"]
        gold["--gold / --gold-pale\nInfo / highlight"]
        sage["--sage / --sage-pale\nSuccess states"]
    end

    subgraph Fonts["Google Fonts"]
        PD["Playfair Display\nHeadings, brand, hero"]
        Lora["Lora\nBody text, labels"]
    end
```

Book cards on the shelf use a `.book-spine` / `.book-spine--friend` left-border accent to visually distinguish own books (rust) from a friend's shelf (alternative colour).

---

## 2. Authentication Design

### 2.1 Username / Password Sign-up Flow

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant hCaptcha as hCaptcha API
    participant Flask
    participant DB as PostgreSQL

    User->>Browser: Fill signup form
    Browser->>Browser: auth.js validates fields (client-side)
    Browser->>hCaptcha: Widget renders, user solves challenge
    hCaptcha-->>Browser: h-captcha-response token
    Browser->>Flask: POST /signup (username, password, confirm, token)
    Flask->>hCaptcha: POST /siteverify (secret, token)
    hCaptcha-->>Flask: {success: true}
    Flask->>DB: SELECT id FROM users WHERE username = ?
    DB-->>Flask: empty (username free)
    Flask->>Flask: bcrypt.hashpw(password)
    Flask->>DB: INSERT INTO users (username, password_hash)
    DB-->>Flask: new user row
    Flask->>Flask: session["user_id"] = new_id
    Flask-->>Browser: 302 → /
```

### 2.2 Username / Password Login Flow

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Flask
    participant DB as PostgreSQL

    User->>Browser: Fill login form
    Browser->>Browser: auth.js validates (client-side)
    Browser->>Flask: POST /login (username, password)
    Flask->>DB: SELECT id, password_hash FROM users WHERE username = ?
    DB-->>Flask: user row (or null)
    Note over Flask: Timing-safe: always runs bcrypt.checkpw<br/>(dummy hash if user not found — avoids<br/>username enumeration via timing)
    Flask->>Flask: bcrypt.checkpw(password, stored_hash)
    alt credentials valid
        Flask->>Flask: session["user_id"] = user.id
        Flask-->>Browser: 302 → /
    else invalid
        Flask-->>Browser: 200 login.html + flash error
    end
```

### 2.3 Google OAuth 2.0 Flow

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Flask
    participant Google as Google OAuth
    participant DB as PostgreSQL

    User->>Browser: Click "Continue with Google"
    Browser->>Flask: GET /auth/google
    Flask->>Flask: Generate random state token → session["oauth_state"]
    Flask-->>Browser: 302 → Google Auth URL (state, client_id, scopes)

    Browser->>Google: Redirect with auth params
    Google->>User: Sign-in / consent screen
    User->>Google: Approve
    Google-->>Browser: 302 → /auth/google/callback?code=...&state=...

    Browser->>Flask: GET /auth/google/callback
    Flask->>Flask: Validate state token (CSRF guard)
    Flask->>Google: POST /token (code, client_secret, redirect_uri)
    Google-->>Flask: access_token
    Flask->>Google: GET /userinfo (Bearer access_token)
    Google-->>Flask: {sub, email, name}

    Flask->>DB: SELECT * FROM users WHERE google_id = sub
    alt existing Google user
        DB-->>Flask: user row
    else email match (link existing account)
        Flask->>DB: SELECT * FROM users WHERE email = ?
        Flask->>DB: UPDATE users SET google_id = ? WHERE id = ?
    else new user
        Flask->>Flask: derive_username(name, email)
        Flask->>DB: INSERT INTO users (username, email, google_id) — password_hash NULL
        DB-->>Flask: new user row
    end

    Flask->>Flask: set_session(user)
    Flask-->>Browser: 302 → /
```

### 2.4 Session & Cookie Security

| Property | Value |
|----------|-------|
| `SESSION_COOKIE_HTTPONLY` | `True` — JavaScript cannot read the cookie |
| `SESSION_COOKIE_SAMESITE` | `Lax` — blocks cross-site form-based CSRF |
| `SESSION_COOKIE_SECURE` | `True` when `FORCE_HTTPS=true` (production) |
| OAuth CSRF | Random `state` token stored in session, verified on callback |
| Login timing | Dummy `bcrypt.checkpw` always runs to prevent username enumeration |

---

## 3. Book Management

### 3.1 Add / Edit Book Flow

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Flask
    participant DB as PostgreSQL

    User->>Browser: Fill book form (title, author, year, rating)
    Browser->>Browser: form.js live validation + star preview
    Browser->>Flask: POST /books/add  (or /books/:id/edit)
    Flask->>Flask: parse_book_form() — server-side validation
    alt validation errors
        Flask-->>Browser: 200 form.html + flash errors (fields pre-filled)
    else valid
        Flask->>DB: INSERT/UPDATE books WHERE user_id = current_user_id()
        Flask-->>Browser: 302 → / + flash success
    end
```

Delete is a `POST /books/:id/delete`. The route guards with `user_id = current_user_id()` so users can never delete another person's book, even with a crafted request.

---

## 4. Social Features

### 4.1 Friend Request Lifecycle

```mermaid
stateDiagram-v2
    [*] --> None : No relationship
    None --> PendingSent : POST /friends/request/:id\n(requester sends)
    PendingSent --> None : POST /friends/decline/:id\n(requester cancels OR addressee declines)
    PendingSent --> Accepted : POST /friends/accept/:id\n(addressee accepts)
    Accepted --> None : POST /friends/remove/:id\n(either party removes)
```

```mermaid
sequenceDiagram
    actor Alice
    actor Bob
    participant Flask
    participant DB as PostgreSQL

    Alice->>Flask: GET /users/search?q=bob
    Flask->>DB: SELECT users WHERE username ILIKE '%bob%' LIMIT 20
    Flask->>DB: friendship_status(alice_id, bob_id) for each result
    Flask-->>Alice: user_search.html — Bob shown with "Add friend" button

    Alice->>Flask: POST /friends/request/bob_id
    Flask->>DB: INSERT INTO friendships (requester_id=Alice, addressee_id=Bob, status='pending')
    Flask-->>Alice: flash "Request sent to bob"

    Note over Bob: Bob sees badge (pending_count > 0) in nav

    Bob->>Flask: GET /friends
    Flask->>DB: SELECT incoming pending WHERE addressee_id = Bob
    Flask-->>Bob: friends.html — Alice shown in "Pending requests"

    Bob->>Flask: POST /friends/accept/:friendship_id
    Flask->>DB: UPDATE friendships SET status='accepted' WHERE id = ? AND addressee_id = Bob
    Flask-->>Bob: flash "You and alice are now friends!"
```

### 4.2 Friend's Shelf — Access Control

```mermaid
sequenceDiagram
    actor User
    participant Flask
    participant DB as PostgreSQL

    User->>Flask: GET /shelf/:target_user_id
    Flask->>Flask: current_user_id() from session
    alt viewing own shelf
        Flask-->>User: 302 → /  (redirect to own index)
    else
        Flask->>DB: are_friends(me, target_user_id)\nSELECT FROM friendships WHERE status='accepted'
        alt not friends
            Flask-->>User: 302 → /friends + flash error
        else friends
            Flask->>DB: SELECT books WHERE user_id = target_user_id ORDER BY title
            Flask-->>User: shelf_view.html (read-only, no edit/delete buttons)
        end
    end
```

### 4.3 Pending Count Badge

A `@app.context_processor` runs on every request for authenticated users. It queries:

```sql
SELECT COUNT(*) AS n
FROM friendships
WHERE addressee_id = :me AND status = 'pending';
```

The result is injected as `{{ pending_count }}` into `base.html`, rendering a badge in the Friends nav link. Exceptions are swallowed silently so a DB hiccup never crashes the entire page render.

---

## 5. Route Map Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | ✅ | User's own shelf |
| GET / POST | `/signup` | ❌ | Create account (username + bcrypt + hCaptcha) |
| GET / POST | `/login` | ❌ | Login with username + password |
| POST | `/logout` | ✅ | Clear session |
| GET | `/auth/google` | ❌ | Initiate Google OAuth |
| GET | `/auth/google/callback` | ❌ | OAuth exchange + session creation |
| GET / POST | `/books/add` | ✅ | Add a book to shelf |
| GET / POST | `/books/<id>/edit` | ✅ | Edit own book |
| POST | `/books/<id>/delete` | ✅ | Delete own book |
| GET | `/friends` | ✅ | Friend management page |
| GET | `/users/search` | ✅ | Search users by username |
| POST | `/friends/request/<id>` | ✅ | Send friend request |
| POST | `/friends/accept/<id>` | ✅ | Accept incoming request |
| POST | `/friends/decline/<id>` | ✅ | Decline / cancel request |
| POST | `/friends/remove/<id>` | ✅ | Remove accepted friend |
| GET | `/shelf/<user_id>` | ✅ | View a friend's shelf (read-only) |
