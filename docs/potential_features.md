# Potential Features

## Business / Product Features

### Social & Discovery
- **Book recommendations from friends** — "Alice and Bob both rated this 4.5+" section on the shelf
- **Activity feed** — chronological stream of friends adding books, so you can see what people are reading right now
- **Book comments / notes** — private reading notes per book, or public comments visible to friends
- **Shared reading lists / clubs** — group shelves where multiple friends can contribute books and discuss
- **"Want to read" status** — separate from the current read shelf; add a wishlist pile alongside the finished pile
- **Reading status tracking** — `reading | finished | abandoned | want_to_read` per book
- **Book page counts + reading progress** — track current page and display a progress bar
- **Follow public profiles** — optional public mode for a shelf so non-friends can browse

### Recommendations & Discovery
- **Similar-book suggestions** — based on what friends with matching tastes are reading
- **AI-powered recommendations** — LLM prompt using user's rated books to generate personalised picks
- **"People who read X also read Y"** — collaborative filtering across all users
- **Browse by genre / tag** — let users tag books and filter by genre across friend shelves
- **Author pages** — aggregate all books by an author across the platform

### Shelf & Book Management
- **Book covers** — fetch cover images from Open Library Covers API using ISBN or title+author
- **ISBN lookup / barcode** — scan ISBN on mobile to auto-fill title, author, year via Open Library / Google Books API
- **Bulk import** — CSV or Goodreads export upload to seed a shelf
- **Export shelf** — download own books as CSV / JSON
- **Reading statistics page** — books per year, average rating, favourite authors/genres, charts
- **Annual reading goal** — set a target count for the year and track progress with a progress bar

### Notifications & Engagement
- **Email notifications** — friend request received, request accepted (opt-in, transactional email via SendGrid / SES)
- **In-app notification centre** — persistent notifications beyond the current nav badge
- **Weekly reading digest email** — summary of what friends added that week

---

## Tech Debt

### Reliability & Scalability
- **Connection pooling** — replace the per-request `psycopg2.connect()` with `psycopg2.pool.ThreadedConnectionPool` or switch to SQLAlchemy with a pool; currently each Gunicorn worker opens a new raw connection per request
- **Database migrations tool** — adopt Alembic (or Flask-Migrate) so schema changes are tracked and reversible; currently schema.sql must be run manually
- **Gunicorn worker count** — hardcoded to 2; should be `(2 × CPU cores) + 1`; make configurable via env var
- **Health-check endpoint** — add `GET /healthz` returning `200 OK` so load-balancers and uptime monitors can probe liveness without touching the DB
- **Structured logging** — replace print-to-stdout with Python `logging` using JSON formatter (so logs are parseable by tools like Loki / Datadog)

### Security Hardening
- **Rate limiting** — add `Flask-Limiter` on `/login`, `/signup`, `/auth/google` to prevent brute-force and credential-stuffing attacks
- **Content Security Policy header** — currently missing; add `Content-Security-Policy` in Nginx to restrict inline scripts and external resource origins
- **CSRF tokens on forms** — `SESSION_COOKIE_SAMESITE=Lax` gives partial CSRF protection; add explicit Flask-WTF CSRF tokens to cover edge cases (cross-site top-level navigation on older browsers)
- **Password reset flow** — Google-only users can recover via OAuth, but native accounts have no recovery path; implement email-based reset with a time-limited signed token
- **Account email verification** — native signup accepts any username with no email; adding optional email enables password recovery and reduces throwaway accounts
- **Secrets rotation** — `SECRET_KEY` rotation invalidates all sessions; add a secondary key slot so old sessions survive a rolling key change

### Developer Experience
- **Automated tests** — zero test coverage currently; add `pytest` + `pytest-flask` with at minimum: auth flow tests, book CRUD ownership checks, friendship state-machine tests
- **CI pipeline** — GitHub Actions workflow: lint (flake8/ruff), run tests, fail PRs that break coverage
- **Docker Compose for local dev** — replace manual `psql` setup with `docker compose up` that boots Flask + Postgres together
- **Environment validation on startup** — assert all required env vars are set at import time; currently missing vars cause cryptic `KeyError` at the first request
- **Pre-commit hooks** — ruff + black for consistent formatting without CI round-trips

### Infrastructure & Operations
- **Off-server database backups** — `backup_db.sh` dumps to `/srv/bookshelf/backups/`; backups should be shipped to Hetzner Object Storage (S3-compatible) or Backblaze B2 for resilience against VM loss
- **Backup integrity checks** — automated restore smoke test (`restore_db.sh`) run on a separate DB to verify the dump is valid
- **VM snapshot automation** — weekly Hetzner snapshot via API to complement the DB backup
- **Monitoring & alerting** — set up UptimeRobot or Better Uptime on the domain; add Prometheus + Grafana (or Grafana Cloud free tier) for request rate, error rate, DB query latency
- **Log rotation** — `/var/log/bookshelf/` grows unbounded; add `logrotate` config
- **Nginx rate limiting** — add `limit_req_zone` in nginx for `/login` and `/signup` as a defence-in-depth layer independent of Flask
- **Static asset versioning / cache busting** — CSS and JS are cached for 7 days (`immutable`); a fingerprinted filename or query-string version param is needed so deploys invalidate caches correctly
- **TLS auto-renewal monitoring** — Let's Encrypt certificates expire every 90 days; verify `certbot.timer` is active and add an alert if renewal fails

