"""
app.py  —  Bookshelf Service
Stack : Flask → Gunicorn → PostgreSQL (psycopg2)
Auth  : username + bcrypt password, Flask session
"""

import os
import bcrypt
import psycopg2
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
    """Decorator: redirect to login if user is not in session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access your shelf.", "info")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def current_user_id():
    return session.get("user_id")


# ── Validation helper ─────────────────────────────────────────────────────────

def parse_book_form(form):
    """
    Validate and coerce book form fields.
    Returns (data_dict, errors_list).
    """
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


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Create a new account."""
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm",  "")

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

        if not errors:
            db = get_db()
            with db.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE username = %s;", (username,))
                if cur.fetchone():
                    errors.append("That username is already taken.")

        if errors:
            for err in errors:
                flash(err, "error")
            return render_template("signup.html", prefill={"username": username})

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

    return render_template("signup.html", prefill={})


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log in to an existing account."""
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

        # Constant-time check; also run check on dummy hash if user missing
        # to avoid timing-based username enumeration
        dummy_hash = b"$2b$12$invalidhashpadding000000000000000000000000000000000000"
        stored = user["password_hash"].encode() if user else dummy_hash
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
    """Clear the session and go to login."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ── Book routes (all require login) ──────────────────────────────────────────

@app.route("/")
@login_required
def index():
    """List books belonging to the logged-in user."""
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

    # Ownership check — user can only edit their own books
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
