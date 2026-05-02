# LinkShelf

LinkShelf is a small Flask bookmark app for saving and sharing useful links with short notes.

## Features

- Public page at `/` that lists saved links
- Admin page at `/admin` for adding and deleting links
- SQLite database for local development
- PostgreSQL support for production with `DATABASE_URL`
- Database tables and placeholder links created automatically on first run
- Render-ready start command: `gunicorn app:app`

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000`.

By default, local development uses `linkshelf.db` in the project folder. To use another database locally, set `DATABASE_URL` before starting the app.

## Deploy on Render

This repo includes `render.yaml`, so Render can create the web service and PostgreSQL database together.

1. Push this repository to GitHub.
2. In Render, choose **New +** and then **Blueprint**.
3. Connect the GitHub repository.
4. Render will read `render.yaml` and create:
   - a Python web service named `linkshelf`
   - a PostgreSQL database named `linkshelf-db`
   - a `DATABASE_URL` environment variable for the app
   - a generated `SECRET_KEY`
5. Deploy the service.

The production start command is:

```bash
gunicorn app:app
```

On startup, the app creates the `links` table if it does not exist. If the table is empty, it adds a few placeholder links.

## Manual Render Setup

If you are not using the blueprint:

1. Create a new Render Web Service from this repo.
2. Set the build command to:

```bash
pip install -r requirements.txt
```

3. Set the start command to:

```bash
gunicorn app:app
```

4. Create a Render PostgreSQL database.
5. Add the database connection string as the web service environment variable `DATABASE_URL`.
6. Add a `SECRET_KEY` environment variable with any long random value.
