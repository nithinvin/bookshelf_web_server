"""
app.py  —  Bookshelf Service
Stack : Flask → Gunicorn → PostgreSQL (psycopg2)
Auth  : username/password (bcrypt) + Google OAuth 2.0 (side-by-side)
        Accounts are linked when Google email matches an existing user's email.
"""

import os
import re
import secrets
import bcrypt
import psycopg2
import requests as http_requests
from psycopg2.extras import RealDictCursor
from functools import wraps
from flask import (
    Flask, g, session,
    render_template, request, redirect, url_for, flash
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]

# ── Session cookie security ───────────────────────────────────────────────────
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FORCE_HTTPS", "false").lower() == "true",
)

# ── hCaptcha ──────────────────────────────────────────────────────────────────
HCAPTCHA_SECRET     = os.environ.get("HCAPTCHA_SECRET_KEY", "")
HCAPTCHA_SITE_KEY   = os.environ.get("HCAPTCHA_SITE_KEY", "")
HCAPTCHA_VERIFY_URL = "https://api.hcaptcha.com/siteverify"

def verify_hcaptcha(token: str) -> bool:
    if not token:
        return False
    try:
        resp = http_requests.post(
            HCAPTCHA_VERIFY_URL,
            data={"secret": HCAPTCHA_SECRET, "response": token},
            timeout=5,
        )
        return resp.json().get("success", False)
    except Exception:
        return False

# ── Google OAuth config ───────────────────────────────────────────────────────
GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_AUTH_URL      = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL     = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL  = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_SCOPES        = "openid email profile"


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(
            host=os.environ["DB_HOST"],
            port=os.environ["DB_PORT"],
            dbname=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            cursor_factory=RealDictCursor,
        )
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ── Auth helpers ──────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access your shelf.", "info")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def current_user_id():
    return session.get("user_id")


def set_session(user):
    """Populate session from a user row dict."""
    session["user_id"]  = user["id"]
    session["username"] = user["username"]


def derive_username(name: str, email: str) -> str:
    """
    Turn a Google display name or email into a clean username candidate.
    Strips non-alphanumeric chars. Falls back to the email local part.
    """
    base = re.sub(r"[^a-z0-9]", "", name.lower()) if name else ""
    if not base:
        base = re.sub(r"[^a-z0-9]", "", email.split("@")[0].lower())
    return base[:40] or "user"


def unique_username(db, base: str) -> str:
    """
    Ensure username is unique. If taken, append a short random suffix.
    """
    candidate = base
    for _ in range(10):
        with db.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = %s;", (candidate,))
            if not cur.fetchone():
                return candidate
        candidate = base + secrets.token_hex(3)   # e.g. "nithin4a2f1c"
    return base + secrets.token_hex(4)             # extremely unlikely to collide


# ── Validation helper ─────────────────────────────────────────────────────────

def parse_book_form(form):
    title  = form.get("title",  "").strip()
    author = form.get("author", "").strip()
    year   = form.get("year",   "").strip()
    rating = form.get("rating", "").strip() or None

    errors = []
    if not title:  errors.append("Title is required.")
    if not author: errors.append("Author is required.")

    if not year:
        errors.append("Publication year is required.")
        year = None
    else:
        try:
            year = int(year)
            if year < 1 or year > 2100:
                raise ValueError
        except ValueError:
            errors.append("Year must be a whole number between 1 and 2100.")
            year = None

    if rating is not None:
        try:
            rating = round(float(rating), 1)
            if not (0.0 <= rating <= 5.0):
                raise ValueError
        except ValueError:
            errors.append("Rating must be between 0.0 and 5.0.")
            rating = None

    if errors:
        return None, errors
    return {"title": title, "author": author, "year": year, "rating": rating}, []


# ── Auth routes — username / password ─────────────────────────────────────────

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        username      = request.form.get("username", "").strip().lower()
        password      = request.form.get("password", "")
        confirm       = request.form.get("confirm",  "")
        captcha_token = request.form.get("h-captcha-response", "")

        errors = []
        if not username:
            errors.append("Username is required.")
        elif len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        elif len(username) > 50:
            errors.append("Username must be 50 characters or fewer.")
        elif not username.isalnum():
            errors.append("Username may only contain letters and numbers.")

        if not password:
            errors.append("Password is required.")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters.")

        if password and confirm != password:
            errors.append("Passwords do not match.")

        if not verify_hcaptcha(captcha_token):
            errors.append("Please complete the captcha.")

        if not errors:
            db = get_db()
            with db.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE username = %s;", (username,))
                if cur.fetchone():
                    errors.append("That username is already taken.")

        if errors:
            for err in errors:
                flash(err, "error")
            return render_template("signup.html",
                                   prefill={"username": username},
                                   hcaptcha_site_key=HCAPTCHA_SITE_KEY)

        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        db = get_db()
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id;",
                (username, pw_hash),
            )
            new_id = cur.fetchone()["id"]
        db.commit()

        session["user_id"]  = new_id
        session["username"] = username
        flash(f"Welcome to your shelf, {username}!", "success")
        return redirect(url_for("index"))

    return render_template("signup.html", prefill={},
                           hcaptcha_site_key=HCAPTCHA_SITE_KEY)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()
        with db.cursor() as cur:
            cur.execute(
                "SELECT id, password_hash FROM users WHERE username = %s;",
                (username,),
            )
            user = cur.fetchone()

        dummy_hash = b"$2b$12$invalidhashpadding000000000000000000000000000000000000"
        stored = user["password_hash"].encode() if (user and user["password_hash"]) else dummy_hash
        match  = bcrypt.checkpw(password.encode(), stored)

        if not user or not match:
            flash("Invalid username or password.", "error")
            return render_template("login.html", prefill={"username": username})

        session["user_id"]  = user["id"]
        session["username"] = username
        flash(f"Welcome back, {username}!", "success")
        return redirect(url_for("index"))

    return render_template("login.html", prefill={})


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ── Auth routes — Google OAuth 2.0 ───────────────────────────────────────────

@app.route("/auth/google")
def google_login():
    """
    Step 1: Redirect the user to Google's consent screen.
    We generate a random 'state' token and store it in the session to
    verify it on the way back — this prevents CSRF on the callback.
    """
    if "user_id" in session:
        return redirect(url_for("index"))

    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    params = {
        "client_id":     GOOGLE_CLIENT_ID,
        "redirect_uri":  url_for("google_callback", _external=True),
        "response_type": "code",
        "scope":         GOOGLE_SCOPES,
        "state":         state,
        "access_type":   "online",
        # 'select_account' forces the account picker even if already signed in,
        # so users with multiple Google accounts can pick the right one.
        "prompt":        "select_account",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return redirect(f"{GOOGLE_AUTH_URL}?{query}")


@app.route("/auth/google/callback")
def google_callback():
    """
    Step 2: Google redirects back here with ?code=...&state=...
    We verify the state, exchange the code for tokens, fetch the user's
    Google profile, then either log them in or create/link their account.
    """
    # ── CSRF check ────────────────────────────────────────────────────────────
    returned_state = request.args.get("state", "")
    expected_state = session.pop("oauth_state", None)
    if not expected_state or returned_state != expected_state:
        flash("Authentication failed (state mismatch). Please try again.", "error")
        return redirect(url_for("login"))

    # ── Error from Google (e.g. user cancelled) ───────────────────────────────
    error = request.args.get("error")
    if error:
        flash("Google sign-in was cancelled or failed.", "error")
        return redirect(url_for("login"))

    code = request.args.get("code")
    if not code:
        flash("No authorisation code received from Google.", "error")
        return redirect(url_for("login"))

    # ── Exchange code for access token ────────────────────────────────────────
    try:
        token_resp = http_requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "code":          code,
                "client_id":     GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri":  url_for("google_callback", _external=True),
                "grant_type":    "authorization_code",
            },
            timeout=10,
        )
        token_resp.raise_for_status()
        token_data   = token_resp.json()
        access_token = token_data.get("access_token")
    except Exception:
        flash("Failed to get token from Google. Please try again.", "error")
        return redirect(url_for("login"))

    # ── Fetch Google profile ──────────────────────────────────────────────────
    try:
        info_resp = http_requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        info_resp.raise_for_status()
        google_info = info_resp.json()
    except Exception:
        flash("Failed to fetch your Google profile. Please try again.", "error")
        return redirect(url_for("login"))

    google_id    = google_info.get("sub")          # stable unique Google user ID
    google_email = google_info.get("email", "")
    google_name  = google_info.get("name",  "")

    if not google_id:
        flash("Google did not return a valid user ID.", "error")
        return redirect(url_for("login"))

    db = get_db()

    # ── Look up existing account ──────────────────────────────────────────────
    # Priority order:
    #   1. Match by google_id         → returning Google user, just log in
    #   2. Match by email             → existing password user, link the accounts
    #   3. No match                   → brand new user, create an account

    with db.cursor() as cur:
        # 1. Already linked?
        cur.execute("SELECT * FROM users WHERE google_id = %s;", (google_id,))
        user = cur.fetchone()

    if not user and google_email:
        with db.cursor() as cur:
            # 2. Email match — link this Google account to the existing user
            cur.execute("SELECT * FROM users WHERE email = %s;", (google_email,))
            user = cur.fetchone()

        if user:
            with db.cursor() as cur:
                cur.execute(
                    "UPDATE users SET google_id = %s WHERE id = %s;",
                    (google_id, user["id"]),
                )
            db.commit()
            flash("Your Google account has been linked to your existing shelf.", "info")

    if not user:
        # 3. New user — derive a username from their Google name/email
        base     = derive_username(google_name, google_email)
        username = unique_username(db, base)

        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO users (username, password_hash, email, google_id)
                   VALUES (%s, NULL, %s, %s) RETURNING *;""",
                (username, google_email or None, google_id),
            )
            user = cur.fetchone()
        db.commit()
        flash(f"Welcome to your shelf, {user['username']}!", "success")

    set_session(user)
    return redirect(url_for("index"))


# ── Book routes (all require login) ──────────────────────────────────────────

@app.route("/")
@login_required
def index():
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT * FROM books WHERE user_id = %s ORDER BY title ASC;",
            (current_user_id(),),
        )
        books = cur.fetchall()
    return render_template("index.html", books=books)


@app.route("/books/add", methods=["GET", "POST"])
@login_required
def add_book():
    if request.method == "POST":
        data, errors = parse_book_form(request.form)
        if errors:
            for err in errors:
                flash(err, "error")
            return render_template("form.html", book=None, prefill=request.form)

        db = get_db()
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO books (user_id, title, author, year, rating) "
                "VALUES (%s, %s, %s, %s, %s);",
                (current_user_id(), data["title"], data["author"],
                 data["year"], data["rating"]),
            )
        db.commit()
        flash(f'"{data["title"]}" added to your shelf.', "success")
        return redirect(url_for("index"))

    return render_template("form.html", book=None, prefill={})


@app.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
@login_required
def edit_book(book_id):
    db = get_db()

    with db.cursor() as cur:
        cur.execute(
            "SELECT * FROM books WHERE id = %s AND user_id = %s;",
            (book_id, current_user_id()),
        )
        book = cur.fetchone()

    if book is None:
        flash("Book not found.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        data, errors = parse_book_form(request.form)
        if errors:
            for err in errors:
                flash(err, "error")
            return render_template("form.html", book=book, prefill=request.form)

        with db.cursor() as cur:
            cur.execute(
                "UPDATE books SET title=%s, author=%s, year=%s, rating=%s "
                "WHERE id=%s AND user_id=%s;",
                (data["title"], data["author"], data["year"], data["rating"],
                 book_id, current_user_id()),
            )
        db.commit()
        flash(f'"{data["title"]}" updated.', "success")
        return redirect(url_for("index"))

    return render_template("form.html", book=book, prefill={})


@app.route("/books/<int:book_id>/delete", methods=["POST"])
@login_required
def delete_book(book_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT title FROM books WHERE id = %s AND user_id = %s;",
            (book_id, current_user_id()),
        )
        book = cur.fetchone()
        if book:
            cur.execute(
                "DELETE FROM books WHERE id = %s AND user_id = %s;",
                (book_id, current_user_id()),
            )
            db.commit()
            flash(f'"{book["title"]}" removed from your shelf.', "success")
        else:
            flash("Book not found.", "error")
    return redirect(url_for("index"))


# ── Health ────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return {"status": "ok"}, 200


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=(os.environ.get("FLASK_ENV") == "development"))
