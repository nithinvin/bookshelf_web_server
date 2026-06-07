"""
app.py – Bookshelf Service
Stack: Flask → Gunicorn → PostgreSQL (via psycopg2)
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, g, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv

# ── Load environment variables ──────────────────────────────────────────────
load_dotenv()

# ── App factory ─────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]


# ── Database helpers ─────────────────────────────────────────────────────────
def get_db():
    """Open a new DB connection if there is none for the current request."""
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
    """Close DB connection at the end of each request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ── Routes ───────────────────────────────────────────────────────────────────
#books_artificial = [{ "id": 100, "title": "Range", "Author": "David", "year": 2018, "rating": 4 }]

@app.route("/")
def index():
    """List all books."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM books ORDER BY title ASC;")
        books = cur.fetchall()
        #print(books)
        #print(type(books))
    return render_template("index.html", books=books)


@app.route("/books/add", methods=["GET", "POST"])
def add_book():
    """Show add form (GET) or create a new book (POST)."""
    if request.method == "POST":
        title  = request.form.get("title",  "").strip()
        author = request.form.get("author", "").strip()
        year   = request.form.get("year",   "").strip()
        rating = request.form.get("rating", "").strip() or None

        # Server-side validation (mirrors client-side checks)
        errors = []
        if not title:  errors.append("Title is required.")
        if not author: errors.append("Author is required.")
        if not year or not year.isdigit():
            errors.append("A valid publication year is required.")
        if rating is not None:
            try:
                rating = float(rating)
                if not (0.0 <= rating <= 5.0):
                    raise ValueError
            except ValueError:
                errors.append("Rating must be between 0.0 and 5.0.")
                rating = None

        if errors:
            for err in errors:
                flash(err, "error")
            return render_template("form.html", book=None)

        db = get_db()
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO books (title, author, year, rating) VALUES (%s, %s, %s, %s);",
                (title, author, int(year), rating),
            )
        db.commit()
        flash(f'"{title}" added to your shelf.', "success")
        return redirect(url_for("index"))

    return render_template("form.html", book=None)


@app.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
def edit_book(book_id):
    """Show edit form (GET) or save changes (POST)."""
    db = get_db()

    if request.method == "POST":
        title  = request.form.get("title",  "").strip()
        author = request.form.get("author", "").strip()
        year   = request.form.get("year",   "").strip()
        rating = request.form.get("rating", "").strip() or None

        errors = []
        if not title:  errors.append("Title is required.")
        if not author: errors.append("Author is required.")
        if not year or not year.isdigit():
            errors.append("A valid publication year is required.")
        if rating is not None:
            try:
                rating = float(rating)
                if not (0.0 <= rating <= 5.0):
                    raise ValueError
            except ValueError:
                errors.append("Rating must be between 0.0 and 5.0.")
                rating = None

        if errors:
            for err in errors:
                flash(err, "error")
            with db.cursor() as cur:
                cur.execute("SELECT * FROM books WHERE id = %s;", (book_id,))
                book = cur.fetchone()
            return render_template("form.html", book=book)

        with db.cursor() as cur:
            cur.execute(
                "UPDATE books SET title=%s, author=%s, year=%s, rating=%s WHERE id=%s;",
                (title, author, int(year), rating, book_id),
            )
        db.commit()
        flash(f'"{title}" updated.', "success")
        return redirect(url_for("index"))

    # GET — load existing record
    with db.cursor() as cur:
        cur.execute("SELECT * FROM books WHERE id = %s;", (book_id,))
        book = cur.fetchone()

    if book is None:
        flash("Book not found.", "error")
        return redirect(url_for("index"))

    return render_template("form.html", book=book)


@app.route("/books/<int:book_id>/delete", methods=["POST"])
def delete_book(book_id):
    """Delete a book."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT title FROM books WHERE id = %s;", (book_id,))
        book = cur.fetchone()
        if book:
            cur.execute("DELETE FROM books WHERE id = %s;", (book_id,))
            db.commit()
            flash(f'"{book["title"]}" removed from your shelf.', "success")
        else:
            flash("Book not found.", "error")
    return redirect(url_for("index"))


@app.route("/health")
def health():
    """Liveness check for the Hetzner deployment."""
    return {"status": "ok"}, 200


# ── Entry point (dev only) ────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=(os.environ.get("FLASK_ENV") == "development"))
