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

Prompts for issue 3 - enhance ui design


› Follow AGENTS.md and use the ui-interactions skill.

Improve the LinkShelf homepage and admin page to
feel like a clean Notion/Excel-style resource table

promot 2 for issue3 (problem - teh webiste look quite bland)

Follow AGENTS.md and use the ui-interactions skill.

The current site looks too bland. Redesign the UI to look more polished, colorful, and portfolio-ready while keeping the app simple.

Focus on:
- stronger homepage header
- card-like layout
- better table styling
- colorful category badges
- improved admin form
- better spacing and typography
- responsive mobile design

Use plain CSS only. Explain changes and how to test.