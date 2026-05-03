---
name: ui-interactions
description: Improve LinkShelf UI, layout, search, filtering, and table interactions.
---

Use this skill when improving the public homepage, admin page, or bookmark table interactions.

Goals:
- Make the app feel like a clean mix of Notion, Airtable, and Excel
- Use spreadsheet-style tables for bookmarks
- Add colorful pill badges for categories
- Add search by title, URL, category, and note
- Add category filters using buttons, tags, or a dropdown
- Improve spacing, typography, and mobile responsiveness
- Add hover states and subtle interactions
- Add clear empty states
- Improve visual hierarchy with headers, cards, and sections
- Make the design feel polished and portfolio-ready

Visual Style:
- Use a soft, modern data-themed color palette
- Prefer navy, slate, teal, blue, and soft neutral backgrounds
- Use card-like containers with subtle borders or shadows
- Use rounded corners consistently
- Make buttons look intentional and clickable
- Keep tables easy to scan with spacing and row hover states
- Avoid a plain/default HTML look

Suggested Palette:
- Background: #f8fafc
- Surface/Card: #ffffff
- Text: #0f172a
- Muted Text: #64748b
- Primary: #0f766e
- Primary Dark: #115e59
- Border: #e2e8f0
- Soft Accent: #ccfbf1

Content UX:
- Homepage should explain what LinkShelf is
- About page should feel professional and personal
- Resource notes should be easy to scan
- Category tags should be visually distinct
- Empty states should guide the user clearly

Rules:
- Use Flask, Jinja, plain CSS, and minimal JavaScript only if needed
- Do not add frontend frameworks
- Do not break existing add/delete functionality
- Keep the code simple and beginner-friendly
- Do not hardcode secrets
- Do not add unnecessary animations or complex components

Testing:
- Verify homepage loads
- Verify admin page loads
- Verify search/filter still works
- Verify add/delete still works
- Verify mobile layout is usable