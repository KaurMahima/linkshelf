import csv
import json
import os
from io import StringIO
from hmac import compare_digest
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
    inspect,
    select,
    text as sql_text,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_environment_file():
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value


load_environment_file()

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
        "LINKSHELF_DATABASE", os.path.join(BASE_DIR, "linkshelf.db")
    )
    return f"sqlite:///{local_path}"


engine = create_engine(get_database_url(), future=True)
metadata = MetaData()
categories_table = Table(
    "categories",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100), nullable=False, unique=True),
    Column("created_at", DateTime, server_default=func.now()),
)
links_table = Table(
    "links",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String(200), nullable=False),
    Column("url", String(500), nullable=False),
    Column("note", String(1000), default=""),
    Column("category_id", Integer),
    Column("is_favorite", Integer, default=0),
    Column("ai_summary", Text, default=""),
    Column("created_at", DateTime, server_default=func.now()),
)


PLACEHOLDER_LINKS = [
    {
        "title": "Flask Documentation",
        "url": "https://flask.palletsprojects.com/",
        "note": "Official Flask docs for routing, templates, and deployment.",
        "category_name": "Docs",
    },
    {
        "title": "Python Documentation",
        "url": "https://docs.python.org/3/",
        "note": "Reference for the Python standard library.",
        "category_name": "Reference",
    },
    {
        "title": "Render Flask Guide",
        "url": "https://render.com/docs/deploy-flask",
        "note": "Deployment notes for running Flask apps on Render.",
        "category_name": "Guide",
    },
]

CATEGORY_STYLES = {
    "Docs": "tag-blue",
    "Guide": "tag-green",
    "Reference": "tag-purple",
    "Tool": "tag-orange",
    "Article": "tag-pink",
}

DEFAULT_CATEGORIES = ["Docs", "Guide", "Reference", "Tool", "Article"]


def init_db():
    metadata.create_all(engine)
    ensure_link_columns()

    with engine.begin() as connection:
        ensure_default_categories(connection)
        count = connection.execute(
            select(func.count()).select_from(links_table)
        ).scalar_one()
        if count == 0:
            for link in PLACEHOLDER_LINKS:
                category_id = get_category_id_by_name(connection, link["category_name"])
                connection.execute(
                    links_table.insert().values(
                        title=link["title"],
                        url=link["url"],
                        note=link["note"],
                        category_id=category_id,
                    )
                )
        fill_missing_categories(connection)


def ensure_link_columns():
    columns = [column["name"] for column in inspect(engine).get_columns("links")]

    with engine.begin() as connection:
        if "ai_summary" not in columns:
            connection.execute(sql_text("ALTER TABLE links ADD COLUMN ai_summary TEXT"))
        if "category_id" not in columns:
            connection.execute(sql_text("ALTER TABLE links ADD COLUMN category_id INTEGER"))
        if "is_favorite" not in columns:
            connection.execute(
                sql_text("ALTER TABLE links ADD COLUMN is_favorite INTEGER DEFAULT 0")
            )


def ensure_default_categories(connection):
    existing = {
        row["name"].lower()
        for row in connection.execute(select(categories_table.c.name)).mappings()
    }
    for name in DEFAULT_CATEGORIES:
        if name.lower() not in existing:
            connection.execute(categories_table.insert().values(name=name))


def fill_missing_categories(connection):
    rows = connection.execute(
        select(
            links_table.c.id,
            links_table.c.title,
            links_table.c.url,
            links_table.c.note,
            links_table.c.category_id,
        )
    ).mappings()

    for link in rows:
        if link["category_id"]:
            continue
        category_name = guess_category_name(link)
        category_id = get_category_id_by_name(connection, category_name)
        connection.execute(
            links_table.update()
            .where(links_table.c.id == link["id"])
            .values(category_id=category_id)
        )


def get_links():
    statement = select(
        links_table.c.id,
        links_table.c.title,
        links_table.c.url,
        links_table.c.note,
        links_table.c.category_id,
        links_table.c.is_favorite,
        links_table.c.ai_summary,
        categories_table.c.name.label("category_name"),
    ).select_from(
        links_table.outerjoin(
            categories_table, links_table.c.category_id == categories_table.c.id
        )
    ).order_by(
        links_table.c.is_favorite.desc(),
        links_table.c.created_at.desc(),
        links_table.c.id.desc(),
    )

    with engine.connect() as connection:
        rows = connection.execute(statement).mappings().all()
        return [decorate_link(row) for row in rows]


def get_categories():
    statement = select(categories_table.c.id, categories_table.c.name).order_by(
        categories_table.c.name
    )
    with engine.connect() as connection:
        return connection.execute(statement).mappings().all()


def decorate_link(link):
    domain = urlparse(link["url"]).netloc.replace("www.", "")
    category = link["category_name"] or guess_category_name(link)

    return {
        "id": link["id"],
        "title": link["title"],
        "url": link["url"],
        "note": link["note"],
        "category_id": link["category_id"],
        "ai_summary": link["ai_summary"] or "",
        "is_favorite": bool(link["is_favorite"]),
        "domain": domain,
        "category": category,
        "tag_class": CATEGORY_STYLES.get(category, "tag-gray"),
    }


def guess_category_name(link):
    text = f"{link['title']} {link['url']} {link['note'] or ''}".lower()

    if "docs" in text or "documentation" in text:
        return "Docs"
    if "guide" in text or "tutorial" in text:
        return "Guide"
    if "reference" in text:
        return "Reference"
    if "tool" in text or "app" in text:
        return "Tool"
    return "Article"


def get_category_id_by_name(connection, name):
    category = connection.execute(
        select(categories_table.c.id).where(
            func.lower(categories_table.c.name) == name.lower()
        )
    ).first()
    return category[0] if category else None


def get_first_category_id(connection):
    category = connection.execute(
        select(categories_table.c.id).order_by(categories_table.c.name)
    ).first()
    return category[0] if category else None


def url_exists(connection, url, link_id=None):
    statement = select(links_table.c.id).where(
        func.lower(links_table.c.url) == url.lower()
    )
    if link_id is not None:
        statement = statement.where(links_table.c.id != link_id)
    return connection.execute(statement).first() is not None


def is_valid_url(url):
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def get_admin_password():
    return os.environ.get("ADMIN_PASSWORD", "")


def is_admin_configured():
    return bool(get_admin_password())


def is_admin_logged_in():
    return session.get("admin_logged_in") is True


def require_admin():
    if is_admin_logged_in():
        return None

    if not is_admin_configured():
        flash("Admin login is disabled until ADMIN_PASSWORD is set.")
    else:
        flash("Please log in to access the admin page.")
    return redirect(url_for("login"))


@app.context_processor
def inject_auth_state():
    return {"admin_logged_in": is_admin_logged_in()}


def generate_ai_summary(title, url, note):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "", "OPENAI_API_KEY is not set for this app process."

    prompt = (
        "Create a concise 4-5 line summary for this saved bookmark. "
        "Keep it practical and useful for someone deciding whether to open it. "
        "Do not use markdown bullets.\n\n"
        f"Title: {title}\n"
        f"URL: {url}\n"
        f"Owner note: {note or 'None'}"
    )
    payload = {
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "instructions": "You write concise bookmark metadata for LinkShelf.",
        "input": prompt,
        "max_output_tokens": 160,
    }
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        details = get_openai_error_message(error)
        app.logger.warning("OpenAI summary generation failed: %s", details)
        return "", details
    except URLError as error:
        details = f"Could not reach OpenAI: {error.reason}"
        app.logger.warning("OpenAI summary generation failed: %s", details)
        return "", details
    except (OSError, json.JSONDecodeError) as error:
        details = f"OpenAI response could not be used: {error}"
        app.logger.warning("OpenAI summary generation failed: %s", details)
        return "", details

    summary = extract_response_text(data)
    lines = [line.strip() for line in summary.splitlines() if line.strip()]
    if not lines:
        return "", "OpenAI returned an empty summary."

    return "\n".join(lines[:5])[:1000], ""


def get_openai_error_message(error):
    try:
        body = json.loads(error.read().decode("utf-8"))
    except (OSError, json.JSONDecodeError):
        body = {}

    message = body.get("error", {}).get("message")
    if message:
        return f"OpenAI API error {error.code}: {message}"

    return f"OpenAI API error {error.code}: {error.reason}"


def extract_response_text(data):
    if data.get("output_text"):
        return data["output_text"].strip()

    text_parts = []
    for item in data.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                text_parts.append(content["text"])

    return "\n".join(text_parts).strip()


@app.route("/")
def index():
    return render_template(
        "index.html",
        links=get_links(),
        categories=get_categories(),
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if is_admin_logged_in():
        return redirect(url_for("admin"))

    admin_password = get_admin_password()
    if request.method == "POST":
        if not admin_password:
            flash("Admin login is disabled until ADMIN_PASSWORD is set.")
        elif compare_digest(request.form.get("password", ""), admin_password):
            session["admin_logged_in"] = True
            flash("Logged in.")
            return redirect(url_for("admin"))
        else:
            flash("Incorrect password.")

    return render_template("login.html", admin_configured=bool(admin_password))


@app.post("/logout")
def logout():
    session.pop("admin_logged_in", None)
    flash("Logged out.")
    return redirect(url_for("index"))


@app.route("/admin", methods=["GET", "POST"])
def admin():
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        url = request.form.get("url", "").strip()
        note = request.form.get("note", "").strip()
        category_id = request.form.get("category_id", type=int)
        is_favorite = 1 if request.form.get("is_favorite") == "on" else 0

        if not title or not url:
            flash("Title and URL are required.")
        elif not is_valid_url(url):
            flash("Please enter a valid http or https URL.")
        else:
            with engine.begin() as connection:
                if url_exists(connection, url):
                    flash("That URL is already saved.")
                    return redirect(url_for("admin"))
                if category_id is None:
                    category_id = get_first_category_id(connection)

                ai_summary, ai_error = generate_ai_summary(title, url, note)
                connection.execute(
                    links_table.insert().values(
                        title=title,
                        url=url,
                        note=note,
                        category_id=category_id,
                        is_favorite=is_favorite,
                        ai_summary=ai_summary,
                    )
                )
            if ai_error:
                flash(f"Link added, but AI summary was not generated: {ai_error}")
            else:
                flash("Link added with AI summary.")
            return redirect(url_for("admin"))

    return render_template(
        "admin.html",
        links=get_links(),
        categories=get_categories(),
    )


@app.post("/admin/edit/<int:link_id>")
def edit_link(link_id):
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    title = request.form.get("title", "").strip()
    url = request.form.get("url", "").strip()
    note = request.form.get("note", "").strip()
    category_id = request.form.get("category_id", type=int)
    is_favorite = 1 if request.form.get("is_favorite") == "on" else 0

    if not title or not url:
        flash("Title and URL are required.")
    elif not is_valid_url(url):
        flash("Please enter a valid http or https URL.")
    else:
        with engine.begin() as connection:
            if url_exists(connection, url, link_id=link_id):
                flash("That URL is already saved.")
                return redirect(url_for("admin"))
            if category_id is None:
                category_id = get_first_category_id(connection)

            connection.execute(
                links_table.update()
                .where(links_table.c.id == link_id)
                .values(
                    title=title,
                    url=url,
                    note=note,
                    category_id=category_id,
                    is_favorite=is_favorite,
                )
            )
        flash("Link updated.")

    return redirect(url_for("admin"))


@app.post("/admin/categories")
def add_category():
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    name = request.form.get("name", "").strip()[:100]
    if not name:
        flash("Category name is required.")
        return redirect(url_for("admin"))

    with engine.begin() as connection:
        if get_category_id_by_name(connection, name):
            flash("That category already exists.")
        else:
            connection.execute(categories_table.insert().values(name=name))
            flash("Category added.")

    return redirect(url_for("admin"))


@app.get("/admin/export.csv")
def export_links():
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["title", "url", "note", "category", "is_favorite"])
    for link in get_links():
        writer.writerow(
            [
                link["title"],
                link["url"],
                link["note"],
                link["category"],
                "yes" if link["is_favorite"] else "no",
            ]
        )

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=linkshelf-links.csv"},
    )


@app.post("/admin/import")
def import_links():
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    upload = request.files.get("csv_file")
    if not upload or not upload.filename:
        flash("Choose a CSV file to import.")
        return redirect(url_for("admin"))

    try:
        content = upload.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        flash("The CSV file must be saved as UTF-8 text.")
        return redirect(url_for("admin"))

    rows = csv.DictReader(StringIO(content))
    added_count = 0
    skipped_count = 0

    with engine.begin() as connection:
        for row in rows:
            title = (row.get("title") or "").strip()
            url = (row.get("url") or "").strip()
            note = (row.get("note") or "").strip()
            category_name = ((row.get("category") or "Article").strip() or "Article")[
                :100
            ]
            favorite_text = (row.get("is_favorite") or "").strip().lower()
            is_favorite = (
                1 if favorite_text in {"1", "true", "yes", "y", "on"} else 0
            )

            if not title or not is_valid_url(url) or url_exists(connection, url):
                skipped_count += 1
                continue

            category_id = get_category_id_by_name(connection, category_name)
            if category_id is None:
                connection.execute(categories_table.insert().values(name=category_name))
                category_id = get_category_id_by_name(connection, category_name)

            connection.execute(
                links_table.insert().values(
                    title=title[:200],
                    url=url[:500],
                    note=note[:1000],
                    category_id=category_id,
                    is_favorite=is_favorite,
                    ai_summary="",
                )
            )
            added_count += 1

    flash(f"Imported {added_count} links. Skipped {skipped_count}.")
    return redirect(url_for("admin"))


@app.post("/admin/delete/<int:link_id>")
def delete_link(link_id):
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    with engine.begin() as connection:
        connection.execute(links_table.delete().where(links_table.c.id == link_id))
    flash("Link deleted.")
    return redirect(url_for("admin"))


init_db()


if __name__ == "__main__":
    app.run()
