import os
from urllib.parse import urlparse

from flask import Flask, flash, redirect, render_template, request, url_for
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine, func, select


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev")


def get_database_url():
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # Render may provide postgres://, but SQLAlchemy expects postgresql://.
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return database_url

    local_path = os.environ.get(
        "LINKSHELF_DATABASE", os.path.join(app.root_path, "linkshelf.db")
    )
    return f"sqlite:///{local_path}"


engine = create_engine(get_database_url(), future=True)
metadata = MetaData()
links_table = Table(
    "links",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String(200), nullable=False),
    Column("url", String(500), nullable=False),
    Column("note", String(1000), default=""),
    Column("created_at", DateTime, server_default=func.now()),
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


def init_db():
    metadata.create_all(engine)

    with engine.begin() as connection:
        count = connection.execute(
            select(func.count()).select_from(links_table)
        ).scalar_one()
        if count == 0:
            connection.execute(
                links_table.insert(),
                PLACEHOLDER_LINKS,
            )


def get_links():
    statement = select(
        links_table.c.id,
        links_table.c.title,
        links_table.c.url,
        links_table.c.note,
    ).order_by(links_table.c.created_at.desc(), links_table.c.id.desc())

    with engine.connect() as connection:
        return connection.execute(statement).mappings().all()


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
            with engine.begin() as connection:
                connection.execute(
                    links_table.insert().values(title=title, url=url, note=note)
                )
            flash("Link added.")
            return redirect(url_for("admin"))

    return render_template("admin.html", links=get_links())


@app.post("/admin/delete/<int:link_id>")
def delete_link(link_id):
    with engine.begin() as connection:
        connection.execute(links_table.delete().where(links_table.c.id == link_id))
    flash("Link deleted.")
    return redirect(url_for("admin"))


init_db()


if __name__ == "__main__":
    app.run(debug=True)
