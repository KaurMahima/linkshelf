import os
import sqlite3
from urllib.parse import urlparse

from flask import Flask, flash, g, redirect, render_template, request, url_for


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev")
app.config["DATABASE"] = os.environ.get(
    "LINKSHELF_DATABASE", os.path.join(app.root_path, "linkshelf.db")
)


PLACEHOLDER_LINKS = [
    {
        "title": "Flask Documentation",
        "url": "https://flask.palletsprojects.com/",
        "note": "Official Flask docs for routing, templates, and deployment.",
    },
    {
        "title": "Python Documentation",
        "url": "https://docs.python.org/3/",
        "note": "Reference for the Python standard library.",
    },
    {
        "title": "Render Flask Guide",
        "url": "https://render.com/docs/deploy-flask",
        "note": "Deployment notes for running Flask apps on Render.",
    },
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(app.config["DATABASE"])
    try:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                note TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        count = db.execute("SELECT COUNT(*) FROM links").fetchone()[0]
        if count == 0:
            db.executemany(
                "INSERT INTO links (title, url, note) VALUES (?, ?, ?)",
                [
                    (link["title"], link["url"], link["note"])
                    for link in PLACEHOLDER_LINKS
                ],
            )
        db.commit()
    finally:
        db.close()


def get_links():
    return get_db().execute(
        "SELECT id, title, url, note FROM links ORDER BY created_at DESC, id DESC"
    ).fetchall()


def is_valid_url(url):
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


@app.route("/")
def index():
    return render_template("index.html", links=get_links())


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        url = request.form.get("url", "").strip()
        note = request.form.get("note", "").strip()

        if not title or not url:
            flash("Title and URL are required.")
        elif not is_valid_url(url):
            flash("Please enter a valid http or https URL.")
        else:
            get_db().execute(
                "INSERT INTO links (title, url, note) VALUES (?, ?, ?)",
                (title, url, note),
            )
            get_db().commit()
            flash("Link added.")
            return redirect(url_for("admin"))

    return render_template("admin.html", links=get_links())


@app.post("/admin/delete/<int:link_id>")
def delete_link(link_id):
    get_db().execute("DELETE FROM links WHERE id = ?", (link_id,))
    get_db().commit()
    flash("Link deleted.")
    return redirect(url_for("admin"))


init_db()


if __name__ == "__main__":
    app.run(debug=True)
