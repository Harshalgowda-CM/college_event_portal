# College Event Statistics Portal

A professional Flask + Supabase web portal for college event operations, participant management, analytics, and CSV download reports.

## Features

- Secure signup and login with hashed passwords
- Professional animated dashboard with rainbow gradient background
- Event creation and participant management
- Event registration tracking
- Analytics summaries
- CSV report download

## Setup

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and add your Supabase project credentials.
4. Run the SQL in [database/schema.sql](/Users/harshalgowdacm/Documents/Codex/2026-04-30-files-mentioned-by-the-user-college/database/schema.sql) inside Supabase SQL editor.
5. Start the app:

```bash
python app.py
```

## Notes

- The login uses `mobile` and `password`.
- The app expects the database tables defined in `database/schema.sql`.
- If Supabase Row Level Security is enabled, add policies that allow your app to read and write the required tables.
