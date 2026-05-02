# LinkShelf

LinkShelf is a small Flask bookmark app for saving and sharing useful links with short notes.

## Features

- Public page at `/` that lists saved links
- Admin page at `/admin` for adding and deleting links
- SQLite database with placeholder links on first run
- Render-ready start command: `gunicorn app:app`

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000`.
