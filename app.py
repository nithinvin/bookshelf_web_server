"""
app.py – Basic Flask startup file (Step 5)
Stack: Flask → Gunicorn → PostgreSQL (via psycopg2)
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, g
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
@app.route("/")
def index():
    """Home / list page – replace with your actual template later."""
    return "<h1>MVP is running</h1><p>Replace this with your Jinja2 template.</p>"


@app.route("/health")
def health():
    """Quick liveness check – useful after deploying to Hetzner."""
    return {"status": "ok"}, 200


# ── Entry point (dev only) ────────────────────────────────────────────────────
# On the Hetzner VM, Gunicorn starts the app instead:
#   gunicorn --workers 2 --bind 0.0.0.0:8000 app:app
if __name__ == "__main__":
    app.run(debug=(os.environ.get("FLASK_ENV") == "development"))
