"""
routes_memory.py  —  Steps 9 & 10
Flask routes wired to an in-memory list instead of PostgreSQL.
Swap this out for the DB-backed routes in app.py once the schema is ready.

Usage:
    FLASK_APP=routes_memory.py flask run
"""

import os
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# ── In-memory store ──────────────────────────────────────────────────────────
# Mirrors the books table: id, title, author, year, rating (float | None)
# This list lives only for the lifetime of the Flask process.

_next_id = 1          # auto-increment counter

BOOKS = [             # a few seed entries so the list page isn't empty
    {"id": 1, "title": "The Name of the Wind",   "author": "Patrick Rothfuss", "year": 2007, "rating": 4.5},
    {"id": 2, "title": "Sapiens",                "author": "Yuval Noah Harari", "year": 2011, "rating": 4.2},
    {"id": 3, "title": "The Hitchhiker's Guide", "author": "Douglas Adams",     "year": 1979, "rating": 4.8},
]
_next_id = len(BOOKS) + 1


# ── Helpers ──────────────────────────────────────────────────────────────────

def find_book(book_id):
    """Return the book dict with the given id, or None."""
    return next((b for b in BOOKS if b["id"] == book_id), None)


def parse_book_form(form):
    """
    Extract and validate form fields.
    Returns (data_dict, errors_list).
    data_dict is None if there are errors.
    """
    title  = form.get("title",  "").strip()
    author = form.get("author", "").strip()
    year   = form.get("year",   "").strip()
    rating = form.get("rating", "").strip() or None

    errors = []

    if not title:
        errors.append("Title is required.")
    if not author:
        errors.append("Author is required.")

    if not year:
        errors.append("Publication year is required.")
        year = None
    else:
        try:
            year = int(year)
            if year < 1 or year > 2100:
                raise ValueError
        except ValueError:
            errors.append("Year must be a number between 1 and 2100.")
            year = None

    if rating is not None:
        try:
            rating = round(float(rating), 1)
            if not (0.0 <= rating <= 5.0):
                raise ValueError
        except ValueError:
            errors.append("Rating must be a number between 0.0 and 5.0.")
            rating = None

    if errors:
        return None, errors

    return {"title": title, "author": author, "year": year, "rating": rating}, []


# ── Routes ───────────────────────────────────────────────────────────────────

# LIST  GET /
@app.route("/")
def index():
    """Show every book in the in-memory list."""
    return render_template("index.html", books=BOOKS)


# ADD   GET  /books/add   → show blank form
#       POST /books/add   → create book, redirect to list
@app.route("/books/add", methods=["GET", "POST"])
def add_book():
    global _next_id

    if request.method == "POST":
        data, errors = parse_book_form(request.form)

        if errors:
            for err in errors:
                flash(err, "error")
            # Re-render the form with the values the user typed so far
            return render_template("form.html", book=None,
                                   prefill=request.form)

        new_book = {"id": _next_id, **data}
        BOOKS.append(new_book)
        _next_id += 1

        flash(f'"{data["title"]}" added to your shelf.', "success")
        return redirect(url_for("index"))

    return render_template("form.html", book=None, prefill={})


# EDIT  GET  /books/<id>/edit  → show form pre-filled with existing data
#       POST /books/<id>/edit  → update book, redirect to list
@app.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
def edit_book(book_id):
    book = find_book(book_id)

    if book is None:
        flash("Book not found.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        data, errors = parse_book_form(request.form)

        if errors:
            for err in errors:
                flash(err, "error")
            return render_template("form.html", book=book,
                                   prefill=request.form)

        # Update the dict in-place so the list reflects the change
        book.update(data)

        flash(f'"{data["title"]}" updated.', "success")
        return redirect(url_for("index"))

    return render_template("form.html", book=book, prefill={})


# DELETE  POST /books/<id>/delete  → remove book, redirect to list
# (POST not GET — deletes should never happen via a plain link)
@app.route("/books/<int:book_id>/delete", methods=["POST"])
def delete_book(book_id):
    global BOOKS
    book = find_book(book_id)

    if book is None:
        flash("Book not found.", "error")
    else:
        BOOKS = [b for b in BOOKS if b["id"] != book_id]
        flash(f'"{book["title"]}" removed from your shelf.', "success")

    return redirect(url_for("index"))


# HEALTH  GET /health
@app.route("/health")
def health():
    return {"status": "ok", "store": "memory", "books": len(BOOKS)}, 200


# ── Dev entry point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
