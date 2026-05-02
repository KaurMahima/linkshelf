Prompts 1 

Follow AGENTS.md. 
Create the initial version of the Linkshelf flask appwith basic struture and placeholder data. 

Prompt 2 (standardized prompt to creare PR's)
Prepare this change for a pull request:
- write a commit message
- write PR title
- write PR description

Prompts for issue 2 

Follow AGENTS.md.

Prepare this Flask app for deployment on Render.

Requirements:
- ensure requirements.txt includes all dependencies (Flask, gunicorn, SQLAlchemy, psycopg2-binary if needed)
- ensure the app runs with: gunicorn app:app
- ensure the app uses DATABASE_URL from environment variables
- support both SQLite (local) and PostgreSQL (production)
- create database tables automatically on startup if they don’t exist
- add a render.yaml file
- update README with clear deployment steps

Keep everything simple and beginner-friendly.
Explain what you change.