"""
Simple URL Shortener - Flask + SQLite
-------------------------------------
POST /api/shorten   -> create a short link
GET  /<code>        -> redirect to the original URL
GET  /api/stats/<c> -> click stats for a short link
GET  /api/recent    -> latest created links
"""
import os
import re
import secrets
import sqlite3
import string
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import Flask, g, jsonify, redirect, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6
CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,32}$")


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DATABASE"] = db_path or os.path.join(BASE_DIR, "urls.db")

    # ---------- database helpers ----------
    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        with sqlite3.connect(app.config["DATABASE"]) as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS urls (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    code         TEXT    NOT NULL UNIQUE,
                    original_url TEXT    NOT NULL,
                    clicks       INTEGER NOT NULL DEFAULT 0,
                    created_at   TEXT    NOT NULL
                )
                """
            )
            db.execute("CREATE INDEX IF NOT EXISTS idx_urls_code ON urls(code)")

    init_db()

    # ---------- logic helpers ----------
    def is_valid_url(value):
        try:
            parsed = urlparse(value)
        except ValueError:
            return False
        return parsed.scheme in ("http", "https") and bool(parsed.netloc) and "." in parsed.netloc

    def generate_code(db):
        # random code; retry on the (very rare) collision
        for _ in range(10):
            code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
            if not db.execute("SELECT 1 FROM urls WHERE code = ?", (code,)).fetchone():
                return code
        raise RuntimeError("Could not generate a unique code")

    # ---------- routes ----------
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.post("/api/shorten")
    def shorten():
        data = request.get_json(silent=True) or {}
        url = (data.get("url") or "").strip()
        custom = (data.get("custom_code") or "").strip()

        if not url:
            return jsonify(error="Please provide a URL."), 400
        if "://" not in url:
            url = "https://" + url
        if not is_valid_url(url):
            return jsonify(error="That doesn't look like a valid http/https URL."), 400
        if len(url) > 2048:
            return jsonify(error="URL is too long (max 2048 characters)."), 400

        db = get_db()
        if custom:
            if not CODE_PATTERN.match(custom):
                return jsonify(error="Custom alias: 3-32 chars, letters/numbers/-/_ only."), 400
            if custom in ("api", "static"):
                return jsonify(error="That alias is reserved."), 400
            if db.execute("SELECT 1 FROM urls WHERE code = ?", (custom,)).fetchone():
                return jsonify(error="That alias is already taken."), 409
            code = custom
        else:
            code = generate_code(db)

        db.execute(
            "INSERT INTO urls (code, original_url, created_at) VALUES (?, ?, ?)",
            (code, url, datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        db.commit()

        short_url = request.host_url.rstrip("/") + "/" + code
        return jsonify(code=code, short_url=short_url, original_url=url), 201

    @app.get("/api/stats/<code>")
    def stats(code):
        row = get_db().execute("SELECT * FROM urls WHERE code = ?", (code,)).fetchone()
        if not row:
            return jsonify(error="Short link not found."), 404
        return jsonify(
            code=row["code"],
            original_url=row["original_url"],
            clicks=row["clicks"],
            created_at=row["created_at"],
        )

    @app.get("/api/recent")
    def recent():
        rows = get_db().execute(
            "SELECT code, original_url, clicks, created_at FROM urls ORDER BY id DESC LIMIT 8"
        ).fetchall()
        base = request.host_url.rstrip("/")
        return jsonify(
            [
                {
                    "code": r["code"],
                    "short_url": f"{base}/{r['code']}",
                    "original_url": r["original_url"],
                    "clicks": r["clicks"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]
        )

    @app.get("/<code>")
    def go(code):
        db = get_db()
        row = db.execute("SELECT original_url FROM urls WHERE code = ?", (code,)).fetchone()
        if not row:
            return render_template("404.html", code=code), 404
        db.execute("UPDATE urls SET clicks = clicks + 1 WHERE code = ?", (code,))
        db.commit()
        return redirect(row["original_url"], code=302)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
