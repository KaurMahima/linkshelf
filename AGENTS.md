# AGENTS.md

## Project Overview

You are building a minimal web application called **LinkShelf**.

LinkShelf is a simple bookmark manager where:

* Users can view saved links on a public page
* The owner can add and delete links from an admin page

---

## Tech Stack

* Python
* Flask
* SQLite (for local development)
* Gunicorn (for production)
* Jinja templates (HTML)
* Simple CSS (no frontend frameworks)

---

## Core Features

* "/" route displays all bookmarks publicly
* "/admin" route allows adding and deleting bookmarks
* Each bookmark includes:

  * title
  * url
  * note (optional)

---

## Development Principles

* Keep the application simple and beginner-friendly
* Avoid unnecessary complexity or abstractions
* Prefer readability over cleverness
* Use minimal file structure:

  * app.py
  * templates/
  * static/
* Do not introduce additional frameworks or libraries unless necessary

---

## UI Guidelines

* Clean and minimal layout
* Easy-to-read list of links
* Mobile-friendly design
* Focus on usability over design complexity

---

## Database Guidelines

* Use SQLite initially
* Keep schema simple and clear
* Avoid complex ORM usage unless explicitly requested

---

## Deployment (Render)

* The application must be deployable on Render as a Web Service
* Use gunicorn as the production server
* The app entry point must be: app:app
* All dependencies must be listed in requirements.txt
* Use environment variables for configuration (e.g., DATABASE_URL)
* Do not hardcode any sensitive values
* Ensure compatibility with PostgreSQL using DATABASE_URL
* Keep deployment setup simple and minimal
---

## Agent Behavior

* Always follow the instructions in this file
* Break tasks into small, manageable steps
* Clearly explain what files are created or modified
* Keep code easy to understand for beginners
* Do not overengineer or add extra features

---

## Workflow Expectations

* Implement features incrementally
* Validate functionality before moving to the next step
* Prefer simple working solutions over complex ones

---

## Security Guidelines

* Never hardcode secrets such as DATABASE_URL, passwords, or API keys
* Always use environment variables for sensitive data
* Do not store secrets in source code or commit them to the repository
* Assume the repository may be public
