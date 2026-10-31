# ✂ Snip — Simple URL Shortener

A tiny URL shortener built with **Flask** and **SQLite**, with a clean glassmorphism frontend.

## Features
- `POST /api/shorten` — turns a long URL into a unique 6-character code
- `GET /<code>` — redirects to the original URL (and counts the click)
- Optional **custom alias** (e.g. `/my-link`)
- URL validation (http/https only; adds `https://` if you forget it)
- Click statistics, recent-links list, copy-to-clipboard button
- Unit tests with pytest

## Project structure
```
url-shortener/
├── app.py              # Flask app: routes, DB, validation
├── requirements.txt
├── README.md
├── templates/
│   ├── index.html      # main page
│   └── 404.html        # unknown short-link page
├── static/
│   ├── style.css       # styling
│   └── app.js          # frontend logic (fetch API)
└── tests/
    └── test_app.py     # pytest tests
```

## Run it
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

The SQLite file `urls.db` is created automatically on first run.

## API

**Create a short link**
```bash
curl -X POST http://127.0.0.1:5000/api/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/a/very/long/link"}'
```
Response (`201`):
```json
{"code": "aB3xYz", "short_url": "http://127.0.0.1:5000/aB3xYz", "original_url": "https://example.com/a/very/long/link"}
```
Optional field: `"custom_code": "my-link"`.

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/shorten` | POST | Create short link |
| `/<code>` | GET | Redirect to original URL |
| `/api/stats/<code>` | GET | Clicks, creation time |
| `/api/recent` | GET | Latest 8 links |

## Database schema
| Column | Type | Notes |
|---|---|---|
| id | INTEGER | primary key |
| code | TEXT | unique short code (indexed) |
| original_url | TEXT | the long URL |
| clicks | INTEGER | redirect counter |
| created_at | TEXT | UTC ISO timestamp |

## Run tests
```bash
pytest -v
```

## How it works
1. The server generates a random 6-char code from `A-Z a-z 0-9` (62⁶ ≈ 56 billion combinations) using `secrets`, retrying on the rare collision.
2. It stores `code → original_url` in SQLite.
3. Visiting `/<code>` looks up the row, increments `clicks`, and sends an HTTP 302 redirect.

## Ideas to extend
- Link expiry dates
- QR code generation
- User accounts / per-user dashboards
- Rate limiting (Flask-Limiter)
- Deploy to Render / Railway with gunicorn
