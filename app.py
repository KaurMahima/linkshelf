import json
import os
from hmac import compare_digest
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from flask import Flask, flash, redirect, render_template, request, session, url_for
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
links_table = Table(
    "links",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String(200), nullable=False),
    Column("url", String(500), nullable=False),
    Column("note", String(1000), default=""),
    Column("ai_summary", Text, default=""),
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

CATEGORY_STYLES = {
    "Docs": "tag-blue",
    "Guide": "tag-green",
    "Reference": "tag-purple",
    "Tool": "tag-orange",
    "Article": "tag-pink",
}


def init_db():
    metadata.create_all(engine)
    ensure_ai_summary_column()

    with engine.begin() as connection:
        count = connection.execute(
            select(func.count()).select_from(links_table)
        ).scalar_one()
        if count == 0:
            connection.execute(
                links_table.insert(),
                PLACEHOLDER_LINKS,
            )


def ensure_ai_summary_column():
    columns = [column["name"] for column in inspect(engine).get_columns("links")]
    if "ai_summary" in columns:
        return

    with engine.begin() as connection:
        connection.execute(sql_text("ALTER TABLE links ADD COLUMN ai_summary TEXT"))


def get_links():
    statement = select(
        links_table.c.id,
        links_table.c.title,
        links_table.c.url,
        links_table.c.note,
        links_table.c.ai_summary,
    ).order_by(links_table.c.created_at.desc(), links_table.c.id.desc())

    with engine.connect() as connection:
        rows = connection.execute(statement).mappings().all()
        return [decorate_link(row) for row in rows]


def decorate_link(link):
    domain = urlparse(link["url"]).netloc.replace("www.", "")
    category = get_category(link)

    return {
        "id": link["id"],
        "title": link["title"],
        "url": link["url"],
        "note": link["note"],
        "ai_summary": link["ai_summary"] or "",
        "domain": domain,
        "category": category,
        "tag_class": CATEGORY_STYLES.get(category, "tag-gray"),
    }


def get_category(link):
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
    return render_template("index.html", links=get_links())


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

        if not title or not url:
            flash("Title and URL are required.")
        elif not is_valid_url(url):
            flash("Please enter a valid http or https URL.")
        else:
            ai_summary, ai_error = generate_ai_summary(title, url, note)
            with engine.begin() as connection:
                connection.execute(
                    links_table.insert().values(
                        title=title,
                        url=url,
                        note=note,
                        ai_summary=ai_summary,
                    )
                )
            if ai_error:
                flash(f"Link added, but AI summary was not generated: {ai_error}")
            else:
                flash("Link added with AI summary.")
            return redirect(url_for("admin"))

    return render_template("admin.html", links=get_links())


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
