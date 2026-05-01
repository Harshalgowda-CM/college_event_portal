import csv
import io
import os
import random
import socket
import sqlite3
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, Response, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "college-event-portal-secret")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "portal_pro.db"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(BASE_DIR, "static", "uploads"))

DEFAULT_DEPARTMENTS = [
    "Computer Science",
    "Information Science",
    "Electronics",
    "Mechanical",
    "Civil",
    "Biotechnology",
    "MBA",
    "MCA",
]

DEFAULT_CATEGORIES = ["Technical", "Cultural", "Sports", "Workshop", "Other"]
FESTIVAL_NAMES = ["ELEGANT", "ECHOES OF YOUTH", "NEXUS"]
EVENT_REQUEST_ROLES = {"faculty", "organiser", "coordinator"}

FESTIVAL_EVENT_BLUEPRINTS = {
    "ELEGANT": [
        ("Classical Dance Finale", "Cultural", True),
        ("Fashion Runway Showcase", "Cultural", True),
        ("Solo Singing League", "Cultural", True),
        ("Campus Theatre Showcase", "Cultural", True),
        ("Photography Storyboard", "Cultural", False),
        ("Creative Writing Arena", "Cultural", True),
        ("Fine Arts Live Wall", "Cultural", False),
        ("Western Group Dance", "Cultural", True),
        ("Folk Rhythm Carnival", "Cultural", True),
        ("Poetry Slam Night", "Cultural", True),
        ("Short Film Premiere", "Cultural", True),
        ("Battle of Bands", "Cultural", True),
        ("Personality and Style Pageant", "Cultural", True),
        ("Open Mic Originals", "Cultural", False),
        ("Literary Debate Forum", "Cultural", True),
        ("Street Art Festival", "Cultural", False),
    ],
    "ECHOES OF YOUTH": [
        ("Inter Department Football Cup", "Sports", True),
        ("Basketball Slam Series", "Sports", True),
        ("Athletics 100 Meter Finals", "Sports", True),
        ("Volleyball Power Spike", "Sports", True),
        ("Table Tennis Masters", "Sports", True),
        ("Badminton Doubles Open", "Sports", True),
        ("Kabaddi Warriors Clash", "Sports", True),
        ("Cricket Super Over League", "Sports", True),
        ("Chess Strategy Classic", "Sports", True),
        ("Marathon for Youth", "Sports", False),
        ("Carrom Challenge", "Sports", True),
        ("Throwball Showdown", "Sports", True),
        ("Yoga Energy Session", "Workshop", False),
        ("Fitness Bootcamp", "Workshop", False),
        ("Adventure Trek Briefing", "Other", False),
        ("Community Leadership Rally", "Other", False),
        ("Open Air Music Evening", "Other", False),
    ],
    "NEXUS": [
        ("AI Innovation Challenge", "Technical", True),
        ("HackSphere 24 Hour Hackathon", "Technical", True),
        ("Robotics Arena", "Technical", True),
        ("Cyber Defense League", "Technical", True),
        ("Cloud Deployment Sprint", "Technical", True),
        ("IoT Smart Campus Expo", "Technical", True),
        ("Code Relay Championship", "Technical", True),
        ("Data Science Insight Cup", "Technical", True),
        ("AR VR Experience Lab", "Technical", False),
        ("Open Source Buildathon", "Technical", False),
        ("Startup Pitch Lab", "Workshop", True),
        ("Resume Building Intensive", "Workshop", False),
        ("UI UX Design Studio", "Workshop", False),
        ("Research Paper Bootcamp", "Workshop", False),
        ("Digital Marketing Playbook", "Workshop", False),
        ("LinkedIn Branding Clinic", "Workshop", False),
        ("Entrepreneurship Incubator Day", "Workshop", False),
    ],
}

FIRST_NAMES = [
    "Aarav", "Diya", "Vihaan", "Anika", "Reyansh", "Ishita", "Advik", "Kavya", "Krish", "Saanvi",
    "Arjun", "Meera", "Vivaan", "Riya", "Sai", "Anvi", "Yash", "Pooja", "Rohan", "Nitya",
    "Harsha", "Tanvi", "Abhinav", "Priya", "Charan", "Manya", "Nikhil", "Lavanya", "Kiran", "Sneha",
]

LAST_NAMES = [
    "Sharma", "Patel", "Rao", "Gowda", "Naik", "Bhat", "Verma", "Kulkarni", "Mehta", "Shetty",
    "Reddy", "Joshi", "Iyer", "Singh", "Chandra", "Das", "Mishra", "Pillai", "Nair", "Jain",
]

VENUES = [
    "Main Auditorium", "Innovation Block", "Sports Complex", "Open Air Theatre", "Convention Centre",
    "Seminar Hall A", "Seminar Hall B", "Central Lawn", "Student Activity Centre", "Library Forum",
]

CHART_TYPES = {
    "bar": "Bar Chart",
    "line": "Line Chart",
    "pie": "Pie Chart",
    "histogram": "Histogram",
    "grouped": "Inter-Department Comparison",
    "students": "Student Distribution Graph",
}


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def find_available_port(start_port):
    port = int(start_port)
    while port <= 65535:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1
    raise RuntimeError("No free port available.")


def table_columns(table_name):
    connection = get_connection()
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    connection.close()
    return {row["name"] for row in rows}


def ensure_column(table_name, column_name, column_type, default_sql=""):
    if column_name not in table_columns(table_name):
        connection = get_connection()
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} {default_sql}".strip()
        )
        connection.commit()
        connection.close()


def init_db():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS portal_users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            mobile TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            department_name TEXT,
            registration_number TEXT UNIQUE,
            participant_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS departments (
            department_id INTEGER PRIMARY KEY AUTOINCREMENT,
            department_name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            parent_festival TEXT NOT NULL DEFAULT 'NEXUS',
            department_id INTEGER,
            category_id INTEGER,
            event_date TEXT,
            venue TEXT,
            description TEXT,
            organizer_name TEXT NOT NULL,
            is_competition INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Approved',
            requested_by INTEGER,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS participants (
            participant_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            participant_name TEXT NOT NULL,
            registration_number TEXT UNIQUE,
            roll_number TEXT,
            department_id INTEGER,
            year_of_study INTEGER,
            participant_type TEXT NOT NULL DEFAULT 'Internal',
            email TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS event_participants (
            event_participant_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            participant_id INTEGER NOT NULL,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(event_id, participant_id)
        );

        CREATE TABLE IF NOT EXISTS competition_results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            participant_id INTEGER NOT NULL,
            rank_position INTEGER NOT NULL,
            award_name TEXT,
            prize_amount REAL DEFAULT 0,
            remarks TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(event_id, rank_position)
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT
        );
        """
    )
    connection.commit()
    connection.close()

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ensure_column("events", "parent_festival", "TEXT", "DEFAULT 'NEXUS'")
    seed_reference_data()
    seed_demo_data()


def seed_reference_data():
    connection = get_connection()
    cursor = connection.cursor()
    for department_name in DEFAULT_DEPARTMENTS:
        cursor.execute("INSERT OR IGNORE INTO departments (department_name) VALUES (?)", (department_name,))
    for category_name in DEFAULT_CATEGORIES:
        cursor.execute("INSERT OR IGNORE INTO categories (category_name) VALUES (?)", (category_name,))
    connection.commit()
    connection.close()


def fetch_table(table_name, order_by=None, descending=False, where=None, params=None):
    connection = get_connection()
    query = f"SELECT * FROM {table_name}"
    values = params or []
    if where:
        query += f" WHERE {where}"
    if order_by:
        direction = "DESC" if descending else "ASC"
        query += f" ORDER BY {order_by} {direction}"
    rows = [dict(row) for row in connection.execute(query, values).fetchall()]
    connection.close()
    return rows


def fetch_single(table_name, where=None, params=None):
    rows = fetch_table(table_name, where=where, params=params)
    return rows[0] if rows else None


def execute(query, params=None):
    connection = get_connection()
    cursor = connection.execute(query, params or [])
    connection.commit()
    lastrowid = cursor.lastrowid
    connection.close()
    return lastrowid


def insert_record(table_name, payload):
    columns = ", ".join(payload.keys())
    placeholders = ", ".join("?" for _ in payload)
    values = [1 if value is True else 0 if value is False else value for value in payload.values()]
    return execute(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})", values)


def update_record(table_name, id_field, record_id, payload):
    assignments = ", ".join(f"{key} = ?" for key in payload.keys())
    values = [1 if value is True else 0 if value is False else value for value in payload.values()]
    values.append(record_id)
    execute(f"UPDATE {table_name} SET {assignments} WHERE {id_field} = ?", values)


def get_setting(setting_key, default_value=None):
    row = fetch_single("app_settings", where="setting_key = ?", params=[setting_key])
    return row["setting_value"] if row else default_value


def set_setting(setting_key, setting_value):
    execute(
        """
        INSERT INTO app_settings (setting_key, setting_value)
        VALUES (?, ?)
        ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
        """,
        [setting_key, setting_value],
    )


def get_departments():
    return fetch_table("departments", order_by="department_name")


def get_categories():
    return fetch_table("categories", order_by="category_name")


def get_department_map():
    return {row["department_id"]: row["department_name"] for row in get_departments()}


def get_category_map():
    return {row["category_id"]: row["category_name"] for row in get_categories()}


def get_current_user():
    if "user_id" not in session:
        return None
    return fetch_single("portal_users", where="user_id = ?", params=[session["user_id"]])


def get_admin_contact_number():
    configured_number = os.getenv("ADMIN_CONTACT_NUMBER")
    if configured_number:
        return configured_number
    host_user = fetch_single("portal_users", where="role = ?", params=["host"])
    return host_user["mobile"] if host_user and host_user.get("mobile") else "9000000000"


def get_user_participant(user_id):
    return fetch_single("participants", where="user_id = ?", params=[user_id])


def get_department_id_by_name(department_name):
    if not department_name:
        return None
    row = fetch_single("departments", where="LOWER(department_name) = LOWER(?)", params=[department_name.strip()])
    return row["department_id"] if row else None


def get_host_manageable_users():
    users = fetch_table("portal_users", order_by="created_at", descending=True)
    users_by_id = {row["user_id"]: row for row in users}
    participants = enrich_participants(fetch_table("participants", order_by="created_at", descending=True))
    participant_by_user_id = {row["user_id"]: row for row in participants if row.get("user_id")}
    for user in users:
        participant = participant_by_user_id.get(user["user_id"])
        user["participant_profile"] = participant
        user["display_registration_number"] = (
            user.get("registration_number")
            or (participant.get("registration_number") if participant else None)
            or "-"
        )
        user["display_department_name"] = (
            user.get("department_name")
            or (participant.get("department_label") if participant else None)
            or "-"
        )
    return list(users_by_id.values())


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to access the portal.", "danger")
            return redirect(url_for("home"))
        return view(*args, **kwargs)

    return wrapped_view


def host_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        user = get_current_user()
        if not user or user.get("role") != "host":
            flash("Only the host can access that section.", "danger")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)

    return wrapped_view


def can_request_event(user):
    return bool(user and user.get("role") in EVENT_REQUEST_ROLES)


def format_date_label(raw_value):
    if not raw_value:
        return "Date to be announced"
    try:
        return datetime.strptime(str(raw_value), "%Y-%m-%d").strftime("%d %b %Y")
    except ValueError:
        return str(raw_value)


def enrich_events(events):
    department_map = get_department_map()
    category_map = get_category_map()
    for event in events:
        event["department_label"] = department_map.get(event.get("department_id"), "Open to all")
        event["category_label"] = category_map.get(event.get("category_id"), "Other")
        event["event_date_label"] = format_date_label(event.get("event_date"))
        event["is_competition"] = bool(event.get("is_competition"))
    return events


def enrich_participants(participants):
    department_map = get_department_map()
    for participant in participants:
        participant["department_label"] = department_map.get(participant.get("department_id"), "Open to all")
    return participants


def visible_events_for(user, include_pending_for_host=False):
    if user and user.get("role") == "host" and include_pending_for_host:
        return enrich_events(fetch_table("events", order_by="event_date"))
    return enrich_events(fetch_table("events", where="status = ?", params=["Approved"], order_by="event_date"))


def events_grouped_by_festival(events):
    grouped = {festival: [] for festival in FESTIVAL_NAMES}
    for event in events:
        grouped.setdefault(event["parent_festival"], []).append(event)
    return grouped


def get_event_participants(event_id):
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT p.*, ep.registered_at
        FROM event_participants ep
        JOIN participants p ON p.participant_id = ep.participant_id
        WHERE ep.event_id = ?
        ORDER BY p.participant_name ASC
        """,
        [event_id],
    ).fetchall()
    connection.close()
    return enrich_participants([dict(row) for row in rows])


def get_results_board():
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT r.*, e.event_name, e.event_date, e.parent_festival, p.participant_name, p.registration_number
        FROM competition_results r
        JOIN events e ON e.event_id = r.event_id
        JOIN participants p ON p.participant_id = r.participant_id
        ORDER BY e.event_date DESC, r.rank_position ASC
        """
    ).fetchall()
    connection.close()
    grouped = []
    bucket = {}
    for row in rows:
        item = dict(row)
        item["event_date_label"] = format_date_label(item["event_date"])
        if item["event_id"] not in bucket:
            bucket[item["event_id"]] = {
                "event_id": item["event_id"],
                "event_name": item["event_name"],
                "parent_festival": item["parent_festival"],
                "event_date_label": item["event_date_label"],
                "winners": [],
            }
            grouped.append(bucket[item["event_id"]])
        bucket[item["event_id"]]["winners"].append(item)
    return grouped


def get_user_history(user_id):
    connection = get_connection()
    history = connection.execute(
        """
        SELECT e.event_name, e.parent_festival, e.event_date, e.venue, ep.registered_at
        FROM event_participants ep
        JOIN participants p ON p.participant_id = ep.participant_id
        JOIN events e ON e.event_id = ep.event_id
        WHERE p.user_id = ?
        ORDER BY e.event_date DESC, ep.registered_at DESC
        """,
        [user_id],
    ).fetchall()
    wins = connection.execute(
        """
        SELECT e.event_name, e.parent_festival, e.event_date, r.rank_position, r.award_name
        FROM competition_results r
        JOIN participants p ON p.participant_id = r.participant_id
        JOIN events e ON e.event_id = r.event_id
        WHERE p.user_id = ?
        ORDER BY e.event_date DESC, r.rank_position ASC
        """,
        [user_id],
    ).fetchall()
    connection.close()
    history_rows = [dict(row) for row in history]
    wins_rows = [dict(row) for row in wins]
    for row in history_rows + wins_rows:
        row["event_date_label"] = format_date_label(row["event_date"])
    return history_rows, wins_rows


def build_dashboard_data(user):
    all_events = enrich_events(fetch_table("events", order_by="event_date"))
    events = all_events if user and user.get("role") == "host" else [event for event in all_events if event["status"] == "Approved"]
    participants = enrich_participants(fetch_table("participants", order_by="created_at", descending=True))
    registrations = fetch_table("event_participants", order_by="registered_at", descending=True)
    results = get_results_board()

    event_lookup = {event["event_id"]: event for event in all_events}
    participant_lookup = {participant["participant_id"]: participant for participant in participants}

    recent_registrations = []
    for row in registrations[:8]:
        event = event_lookup.get(row["event_id"])
        participant = participant_lookup.get(row["participant_id"])
        if event and participant:
            recent_registrations.append(
                {
                    "event_name": event["event_name"],
                    "festival": event["parent_festival"],
                    "participant_name": participant["participant_name"],
                    "registered_at": row["registered_at"],
                }
            )

    today = date.today()
    upcoming_events = []
    for event in events:
        if event.get("event_date"):
            try:
                event_day = datetime.strptime(event["event_date"], "%Y-%m-%d").date()
            except ValueError:
                continue
            if event_day >= today:
                upcoming_events.append(event)
    upcoming_events = upcoming_events[:6]

    event_counter = Counter()
    festival_counter = Counter(event["parent_festival"] for event in events)
    for row in registrations:
        event = event_lookup.get(row["event_id"])
        if event and (user.get("role") == "host" or event["status"] == "Approved"):
            event_counter[event["event_name"]] += 1

    top_events = []
    for label, value in event_counter.most_common(6):
        top_events.append(
            {
                "label": label,
                "value": value,
                "share": round((value / len(registrations)) * 100, 1) if registrations else 0,
            }
        )
    top_events_total = sum(item["value"] for item in top_events)

    my_history, my_wins = ([], [])
    if user.get("role") != "host":
        my_history, my_wins = get_user_history(user["user_id"])

    return {
        "stats": {
            "participants": len(participants),
            "events": len(all_events),
            "approved_events": len([event for event in all_events if event["status"] == "Approved"]),
            "registrations": len(registrations),
            "pending_requests": len([event for event in all_events if event["status"] == "Pending"]),
            "announced_results": len(results),
            "my_events": len(my_history),
            "my_wins": len(my_wins),
        },
        "events": events,
        "upcoming_events": upcoming_events,
        "recent_registrations": recent_registrations,
        "results_preview": results[:4],
        "top_events": top_events,
        "top_events_total": top_events_total,
        "festival_counter": festival_counter,
        "my_history": my_history[:5],
        "my_wins": my_wins[:5],
        "pending_requests": [event for event in all_events if event["status"] == "Pending"][:6],
    }


def seed_demo_data():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO portal_users (full_name, mobile, password_hash, role, department_name, registration_number)
        VALUES (?, ?, ?, 'host', ?, ?)
        """,
        ("Campus Event Host", "9000000000", generate_password_hash("host123"), "Administration", "HOST-001"),
    )

    department_rows = cursor.execute("SELECT department_id, department_name FROM departments").fetchall()
    category_rows = cursor.execute("SELECT category_id, category_name FROM categories").fetchall()
    department_map = {row["department_name"]: row["department_id"] for row in department_rows}
    category_map = {row["category_name"]: row["category_id"] for row in category_rows}
    host_id = cursor.execute("SELECT user_id FROM portal_users WHERE role = 'host' LIMIT 1").fetchone()["user_id"]

    existing_festivals = {row["parent_festival"] for row in cursor.execute("SELECT parent_festival FROM events").fetchall()}
    total_blueprint_events = sum(len(items) for items in FESTIVAL_EVENT_BLUEPRINTS.values())
    current_event_count = cursor.execute("SELECT COUNT(*) AS total FROM events").fetchone()["total"]

    if existing_festivals != set(FESTIVAL_NAMES) or current_event_count != total_blueprint_events:
        cursor.execute("DELETE FROM competition_results")
        cursor.execute("DELETE FROM event_participants")
        cursor.execute("DELETE FROM events")
        start_day = date.today() - timedelta(days=12)
        offset = 0
        for festival_name, blueprint_rows in FESTIVAL_EVENT_BLUEPRINTS.items():
            for event_name, category_name, is_competition in blueprint_rows:
                department_name = DEFAULT_DEPARTMENTS[offset % len(DEFAULT_DEPARTMENTS)]
                event_date = (start_day + timedelta(days=offset + 1)).isoformat()
                cursor.execute(
                    """
                    INSERT INTO events (
                        event_name, parent_festival, department_id, category_id, event_date, venue, description,
                        organizer_name, is_competition, status, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Approved', ?)
                    """,
                    (
                        event_name,
                        festival_name,
                        department_map[department_name],
                        category_map[category_name],
                        event_date,
                        VENUES[offset % len(VENUES)],
                        f"{event_name} is an official university event under {festival_name}, designed for a strong campus experience.",
                        "Campus Event Host",
                        1 if is_competition else 0,
                        host_id,
                    ),
                )
                offset += 1

    participant_count = cursor.execute("SELECT COUNT(*) AS total FROM participants").fetchone()["total"]
    if participant_count < 250:
        for index in range(participant_count, 250):
            full_name = f"{FIRST_NAMES[index % len(FIRST_NAMES)]} {LAST_NAMES[(index * 3) % len(LAST_NAMES)]}"
            registration_number = f"REG2026{index + 1:03d}"
            department_name = DEFAULT_DEPARTMENTS[index % len(DEFAULT_DEPARTMENTS)]
            cursor.execute(
                """
                INSERT OR IGNORE INTO participants (
                    user_id, participant_name, registration_number, roll_number, department_id, year_of_study,
                    participant_type, email, phone
                ) VALUES (?, ?, ?, ?, ?, ?, 'Internal', ?, ?)
                """,
                (
                    None,
                    full_name,
                    registration_number,
                    registration_number,
                    department_map[department_name],
                    (index % 4) + 1,
                    f"student{index + 1}@university.edu",
                    f"98{index + 10000000:08d}"[:10],
                ),
            )

    registration_count = cursor.execute("SELECT COUNT(*) AS total FROM event_participants").fetchone()["total"]
    if registration_count < 360:
        cursor.execute("DELETE FROM competition_results")
        cursor.execute("DELETE FROM event_participants")
        event_rows = cursor.execute("SELECT event_id, is_competition FROM events").fetchall()
        event_ids = [row["event_id"] for row in event_rows]
        participant_ids = [row["participant_id"] for row in cursor.execute("SELECT participant_id FROM participants").fetchall()]
        random.seed(42)
        used_pairs = set()
        for participant_id in participant_ids:
            sample_size = random.randint(1, 3)
            for event_id in random.sample(event_ids, k=sample_size):
                pair = (event_id, participant_id)
                if pair in used_pairs:
                    continue
                used_pairs.add(pair)
                cursor.execute(
                    "INSERT OR IGNORE INTO event_participants (event_id, participant_id) VALUES (?, ?)",
                    (event_id, participant_id),
                )

        competition_event_ids = [row["event_id"] for row in event_rows if row["is_competition"]]
        for event_id in competition_event_ids[:18]:
            candidates = cursor.execute(
                "SELECT participant_id FROM event_participants WHERE event_id = ? LIMIT 6",
                (event_id,),
            ).fetchall()
            if len(candidates) >= 3:
                for rank_position, participant_row in enumerate(candidates[:3], start=1):
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO competition_results (
                            event_id, participant_id, rank_position, award_name, prize_amount, remarks
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event_id,
                            participant_row["participant_id"],
                            rank_position,
                            ["Winner", "Runner Up", "Second Runner Up"][rank_position - 1],
                            [10000, 6000, 3000][rank_position - 1],
                            "Seeded demo result",
                        ),
                    )

    connection.commit()
    connection.close()


def chart_payload(festival_filter):
    events = enrich_events(fetch_table("events", order_by="event_date"))
    if festival_filter and festival_filter != "ALL":
        events = [event for event in events if event["parent_festival"] == festival_filter]
    event_ids = [event["event_id"] for event in events]
    if event_ids:
        placeholders = ", ".join("?" for _ in event_ids)
        registrations = fetch_table("event_participants", where=f"event_id IN ({placeholders})", params=event_ids)
    else:
        registrations = []
    participants = enrich_participants(fetch_table("participants"))

    event_lookup = {event["event_id"]: event for event in events}
    participant_lookup = {participant["participant_id"]: participant for participant in participants}

    category_counter = Counter(event["category_label"] for event in events)
    popularity_counter = Counter()
    daily_counter = Counter()
    registration_distribution = []
    grouped_counter = defaultdict(lambda: Counter())
    student_department_counter = Counter(participant["department_label"] for participant in participants)
    student_year_counter = Counter(str(participant["year_of_study"] or "Unknown") for participant in participants)

    per_event_registration = Counter()
    for row in registrations:
        event = event_lookup.get(row["event_id"])
        participant = participant_lookup.get(row["participant_id"])
        if not event:
            continue
        popularity_counter[event["event_name"]] += 1
        per_event_registration[event["event_name"]] += 1
        if event.get("event_date"):
            daily_counter[event["event_date_label"]] += 1
        if participant:
            grouped_counter[participant["department_label"]][event["parent_festival"]] += 1

    registration_distribution.extend(per_event_registration.values())
    return {
        "events": events,
        "category_counter": category_counter,
        "popularity_counter": popularity_counter,
        "daily_counter": daily_counter,
        "registration_distribution": registration_distribution or [0],
        "grouped_counter": grouped_counter,
        "student_department_counter": student_department_counter,
        "student_year_counter": student_year_counter,
    }


def render_chart(chart_type, festival_filter):
    payload = chart_payload(festival_filter)
    fig, ax = plt.subplots(figsize=(9, 4.8), facecolor="#0b1020")
    ax.set_facecolor("#10172b")
    title_suffix = festival_filter if festival_filter and festival_filter != "ALL" else "All Festivals"

    if chart_type == "bar":
        items = payload["popularity_counter"].most_common(8)
        labels = [item[0] for item in items] or ["No data"]
        values = [item[1] for item in items] or [0]
        ax.bar(labels, values, color="#59e8ff")
        ax.set_title(f"Event Popularity - {title_suffix}", color="white")
        ax.tick_params(axis="x", rotation=25, colors="white")
        ax.tick_params(axis="y", colors="white")
    elif chart_type == "line":
        ordered = sorted(payload["daily_counter"].items(), key=lambda item: datetime.strptime(item[0], "%d %b %Y") if item[0] != "Date to be announced" else datetime.today())
        labels = [item[0] for item in ordered] or ["No data"]
        values = [item[1] for item in ordered] or [0]
        ax.plot(labels, values, color="#ff61c7", linewidth=3, marker="o")
        ax.fill_between(range(len(values)), values, color="#ff61c7", alpha=0.15)
        ax.set_title(f"Registration Trend - {title_suffix}", color="white")
        ax.tick_params(axis="x", rotation=25, colors="white")
        ax.tick_params(axis="y", colors="white")
    elif chart_type == "pie":
        items = payload["category_counter"].most_common()
        labels = [item[0] for item in items] or ["No data"]
        values = [item[1] for item in items] or [1]
        colors = ["#59e8ff", "#ff61c7", "#ffd76d", "#79ffb5", "#8c79ff"][: len(labels)]
        ax.pie(values, labels=labels, autopct="%1.1f%%", colors=colors, textprops={"color": "white"})
        ax.set_title(f"Category Share - {title_suffix}", color="white")
    elif chart_type == "histogram":
        ax.hist(payload["registration_distribution"], bins=min(8, max(payload["registration_distribution"]) + 1), color="#ffd76d", edgecolor="#0b1020")
        ax.set_title(f"Registrations Per Event Distribution - {title_suffix}", color="white")
        ax.tick_params(axis="x", colors="white")
        ax.tick_params(axis="y", colors="white")
    elif chart_type == "grouped":
        top_departments = list(payload["grouped_counter"].keys())[:5] or ["No data"]
        x_positions = list(range(len(top_departments)))
        width = 0.22
        colors = {"ELEGANT": "#59e8ff", "ECHOES OF YOUTH": "#ff61c7", "NEXUS": "#ffd76d"}
        for index, festival_name in enumerate(FESTIVAL_NAMES):
            festival_values = [payload["grouped_counter"][department].get(festival_name, 0) for department in top_departments]
            shifted = [position + (index - 1) * width for position in x_positions]
            ax.bar(shifted, festival_values, width=width, label=festival_name, color=colors[festival_name])
        ax.set_xticks(x_positions)
        ax.set_xticklabels(top_departments, rotation=20, color="white")
        ax.tick_params(axis="y", colors="white")
        ax.legend(facecolor="#10172b", edgecolor="#1d2746", labelcolor="white")
        ax.set_title(f"Inter-Department Festival Comparison - {title_suffix}", color="white")
    elif chart_type == "students":
        department_items = payload["student_department_counter"].most_common(8)
        labels = [item[0] for item in department_items] or ["No data"]
        values = [item[1] for item in department_items] or [0]
        ax.bar(labels, values, color="#79ffb5")
        ax2 = ax.twinx()
        year_items = sorted(payload["student_year_counter"].items(), key=lambda item: item[0])
        year_labels = [item[0] for item in year_items]
        year_values = [item[1] for item in year_items]
        if year_labels:
            ax2.plot(range(len(year_labels)), year_values, color="#ffd76d", linewidth=2.5, marker="o")
            ax2.set_yticks([])
        ax.set_title(f"Student Distribution - {title_suffix}", color="white")
        ax.tick_params(axis="x", rotation=22, colors="white")
        ax.tick_params(axis="y", colors="white")
        ax2.spines["right"].set_color("#1d2746")
    else:
        ax.text(0.5, 0.5, "Unknown chart", ha="center", va="center", color="white")
        ax.axis("off")

    if chart_type != "pie":
        for spine in ax.spines.values():
            spine.set_color("#1d2746")
        ax.grid(axis="y", color="#1d2746", alpha=0.4)

    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", facecolor=fig.get_facecolor(), dpi=160)
    plt.close(fig)
    buffer.seek(0)
    return buffer.getvalue()


@app.context_processor
def inject_globals():
    return {
        "current_user": get_current_user(),
        "festival_names": FESTIVAL_NAMES,
        "public_logo": get_setting("public_logo"),
        "admin_contact_number": get_admin_contact_number(),
        "event_request_roles": sorted(EVENT_REQUEST_ROLES),
    }


@app.route("/")
def home():
    return render_template("auth.html")


@app.route("/signup", methods=["POST"])
def signup():
    full_name = request.form.get("full_name", "").strip()
    mobile = request.form.get("mobile", "").strip()
    password = request.form.get("password", "").strip()
    department_name = request.form.get("department_name", "").strip()
    registration_number = request.form.get("registration_number", "").strip().upper()

    if not all([full_name, mobile, password, registration_number]):
        flash("All signup fields are required.", "danger")
        return redirect(url_for("home"))

    if fetch_single("portal_users", where="mobile = ?", params=[mobile]):
        flash("A user with that mobile number already exists.", "danger")
        return redirect(url_for("home"))

    if fetch_single("portal_users", where="registration_number = ?", params=[registration_number]):
        flash("That registration number is already linked to an account.", "danger")
        return redirect(url_for("home"))

    department = fetch_single("departments", where="department_name = ?", params=[department_name]) if department_name else None
    user_id = insert_record(
        "portal_users",
        {
            "full_name": full_name,
            "mobile": mobile,
            "password_hash": generate_password_hash(password),
            "role": "student",
            "department_name": department_name or None,
            "registration_number": registration_number,
        },
    )
    participant_id = insert_record(
        "participants",
        {
            "user_id": user_id,
            "participant_name": full_name,
            "registration_number": registration_number,
            "roll_number": registration_number,
            "department_id": department["department_id"] if department else None,
            "year_of_study": None,
            "participant_type": "Internal",
            "email": None,
            "phone": mobile,
        },
    )
    update_record("portal_users", "user_id", user_id, {"participant_id": participant_id})
    flash("Account created successfully. Please login.", "success")
    return redirect(url_for("home"))


@app.route("/login", methods=["POST"])
def login():
    mobile = request.form.get("mobile", "").strip()
    password = request.form.get("password", "").strip()
    user = fetch_single("portal_users", where="mobile = ?", params=[mobile])
    if not user or not check_password_hash(user["password_hash"], password):
        flash("Invalid mobile number or password.", "danger")
        return redirect(url_for("home"))
    session["user_id"] = user["user_id"]
    session["role"] = user["role"]
    flash(f"Welcome back, {user['full_name']}.", "success")
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    data = build_dashboard_data(user)
    return render_template("dashboard.html", active_page="dashboard", user_name=user["full_name"], **data)


@app.route("/branding", methods=["POST"])
@login_required
@host_required
def branding():
    photo = request.files.get("public_logo")
    if not photo or not photo.filename:
        flash("Please choose a logo image to upload.", "danger")
        return redirect(url_for("dashboard"))

    extension = os.path.splitext(photo.filename)[1].lower()
    if extension not in {".png", ".jpg", ".jpeg", ".webp"}:
        flash("Please upload a PNG, JPG, JPEG, or WEBP logo.", "danger")
        return redirect(url_for("dashboard"))

    filename = secure_filename(f"public_logo{extension}")
    file_path = os.path.join(UPLOAD_DIR, filename)
    photo.save(file_path)
    set_setting("public_logo", f"uploads/{filename}")
    flash("Public portal logo updated successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/host/accounts", methods=["POST"])
@login_required
@host_required
def create_host_account():
    full_name = request.form.get("full_name", "").strip()
    mobile = request.form.get("mobile", "").strip()
    password = request.form.get("password", "").strip()
    role = request.form.get("role", "").strip().lower()
    department_name = request.form.get("department_name", "").strip()

    if role not in EVENT_REQUEST_ROLES:
        flash("Please select a valid account type.", "danger")
        return redirect(url_for("host_accounts"))
    if not full_name or not mobile or not password:
        flash("Name, phone number, and password are required.", "danger")
        return redirect(url_for("host_accounts"))
    if fetch_single("portal_users", where="mobile = ?", params=[mobile]):
        flash("A user with that phone number already exists.", "danger")
        return redirect(url_for("host_accounts"))
    if role == "faculty" and not department_name:
        flash("Department is required for faculty accounts.", "danger")
        return redirect(url_for("host_accounts"))

    insert_record(
        "portal_users",
        {
            "full_name": full_name,
            "mobile": mobile,
            "password_hash": generate_password_hash(password),
            "role": role,
            "department_name": department_name or None,
            "registration_number": None,
            "participant_id": None,
        },
    )
    flash(f"{role.title()} account created successfully.", "success")
    return redirect(url_for("host_accounts"))


@app.route("/host/accounts/update/<int:user_id>", methods=["POST"])
@login_required
@host_required
def update_host_managed_user(user_id):
    target_user = fetch_single("portal_users", where="user_id = ?", params=[user_id])
    if not target_user:
        flash("User account not found.", "danger")
        return redirect(url_for("host_accounts"))

    full_name = request.form.get("full_name", "").strip()
    mobile = request.form.get("mobile", "").strip()
    role = request.form.get("role", "").strip().lower()
    department_name = request.form.get("department_name", "").strip()
    registration_number = request.form.get("registration_number", "").strip()
    password = request.form.get("password", "").strip()

    if not full_name or not mobile:
        flash("Name and phone number are required.", "danger")
        return redirect(url_for("host_accounts", edit_user_id=user_id))
    if role not in {"host", "student", "faculty", "organiser", "coordinator"}:
        flash("Please select a valid role.", "danger")
        return redirect(url_for("host_accounts", edit_user_id=user_id))

    existing_mobile = fetch_single("portal_users", where="mobile = ? AND user_id != ?", params=[mobile, user_id])
    if existing_mobile:
        flash("Another account already uses that phone number.", "danger")
        return redirect(url_for("host_accounts", edit_user_id=user_id))

    participant = get_user_participant(user_id)
    payload = {
        "full_name": full_name,
        "mobile": mobile,
        "role": role,
        "department_name": department_name or None,
    }

    if role == "student":
        if not registration_number:
            flash("Registration number is required for student accounts.", "danger")
            return redirect(url_for("host_accounts", edit_user_id=user_id))
        existing_registration = fetch_single(
            "portal_users",
            where="registration_number = ? AND user_id != ?",
            params=[registration_number, user_id],
        )
        if existing_registration:
            flash("Another account already uses that registration number.", "danger")
            return redirect(url_for("host_accounts", edit_user_id=user_id))
        existing_participant_registration = fetch_single(
            "participants",
            where="registration_number = ? AND user_id != ?",
            params=[registration_number, user_id],
        )
        if existing_participant_registration:
            flash("Another participant already uses that registration number.", "danger")
            return redirect(url_for("host_accounts", edit_user_id=user_id))
        payload["registration_number"] = registration_number
    else:
        payload["registration_number"] = None

    if role == "faculty" and not department_name:
        flash("Department is required for faculty accounts.", "danger")
        return redirect(url_for("host_accounts", edit_user_id=user_id))

    if password:
        payload["password_hash"] = generate_password_hash(password)

    update_record("portal_users", "user_id", user_id, payload)

    if participant:
        participant_department_id = get_department_id_by_name(department_name) if department_name else participant.get("department_id")
        participant_payload = {
            "participant_name": full_name,
            "registration_number": registration_number or None,
            "roll_number": registration_number or participant.get("roll_number"),
            "phone": mobile,
        }
        if participant_department_id:
            participant_payload["department_id"] = participant_department_id
        update_record("participants", "participant_id", participant["participant_id"], participant_payload)

    flash("User account updated successfully.", "success")
    return redirect(url_for("host_accounts"))


@app.route("/host/accounts/delete/<int:user_id>", methods=["POST"])
@login_required
@host_required
def delete_host_managed_user(user_id):
    current_user = get_current_user()
    if current_user and current_user["user_id"] == user_id:
        flash("You cannot delete the currently logged-in host account.", "danger")
        return redirect(url_for("host_accounts"))

    target_user = fetch_single("portal_users", where="user_id = ?", params=[user_id])
    if not target_user:
        flash("User account not found.", "danger")
        return redirect(url_for("host_accounts"))

    participant = get_user_participant(user_id)
    if participant:
        execute("DELETE FROM competition_results WHERE participant_id = ?", [participant["participant_id"]])
        execute("DELETE FROM event_participants WHERE participant_id = ?", [participant["participant_id"]])
        execute("DELETE FROM participants WHERE participant_id = ?", [participant["participant_id"]])

    execute("DELETE FROM portal_users WHERE user_id = ?", [user_id])
    flash("User account deleted successfully.", "success")
    return redirect(url_for("host_accounts"))


@app.route("/host/accounts")
@login_required
@host_required
def host_accounts():
    competition_events = [event for event in enrich_events(fetch_table("events", order_by="event_date")) if event["is_competition"]]
    selected_edit_user_id = request.args.get("edit_user_id", type=int)
    managed_users = get_host_manageable_users()
    editable_user = next((row for row in managed_users if row["user_id"] == selected_edit_user_id), None)
    return render_template(
        "results.html",
        active_page="create_account",
        competition_events=competition_events,
        selected_event=None,
        selected_event_id=None,
        selected_participants=[],
        winner_map={},
        results_board=get_results_board(),
        host_staff_accounts=fetch_table("portal_users", where="role IN ('faculty','organiser','coordinator')", order_by="created_at", descending=True),
        managed_users=managed_users,
        editable_user=editable_user,
        departments=get_departments(),
        show_create_account=True,
    )


@app.route("/events", methods=["GET", "POST"])
@login_required
def events():
    user = get_current_user()
    edit_id = request.args.get("edit_id", type=int)
    edit_event = fetch_single("events", where="event_id = ?", params=[edit_id]) if edit_id and user["role"] == "host" else None

    if request.method == "POST":
        if user["role"] != "host" and not can_request_event(user):
            flash("Only faculty, organisers, and coordinators can request new events.", "danger")
            return redirect(url_for("events"))
        payload = {
            "event_name": request.form.get("event_name", "").strip(),
            "parent_festival": request.form.get("parent_festival", "NEXUS"),
            "department_id": request.form.get("department_id", type=int),
            "category_id": request.form.get("category_id", type=int),
            "event_date": request.form.get("event_date") or None,
            "venue": request.form.get("venue", "").strip() or None,
            "description": request.form.get("description", "").strip() or None,
            "organizer_name": request.form.get("organizer_name", "").strip() or user["full_name"],
            "is_competition": request.form.get("is_competition") == "on",
            "status": "Approved" if user["role"] == "host" else "Pending",
            "requested_by": user["user_id"] if user["role"] != "host" else None,
            "created_by": user["user_id"] if user["role"] == "host" else None,
        }
        if user["role"] == "host" and request.form.get("status"):
            payload["status"] = request.form.get("status")
        if user["role"] == "host" and request.form.get("event_id", type=int):
            update_record("events", "event_id", request.form.get("event_id", type=int), payload)
            flash("Event updated successfully.", "success")
        else:
            insert_record("events", payload)
            flash("Event created successfully." if user["role"] == "host" else "Event request sent to host for approval.", "success")
        return redirect(url_for("events"))

    all_events = enrich_events(fetch_table("events", order_by="event_date"))
    visible_events = visible_events_for(user, include_pending_for_host=user["role"] == "host")
    pending_requests = [event for event in all_events if event["status"] == "Pending"]
    return render_template(
        "events.html",
        active_page="events",
        events=visible_events,
        all_events=all_events,
        departments=get_departments(),
        categories=get_categories(),
        pending_requests=pending_requests,
        edit_event=edit_event,
        event_groups=events_grouped_by_festival(visible_events),
        can_request=can_request_event(user),
    )


@app.route("/event-action/<int:event_id>/<action>", methods=["POST"])
@login_required
@host_required
def event_action(event_id, action):
    if action not in {"approve", "reject"}:
        flash("Invalid event action.", "danger")
        return redirect(url_for("events"))
    update_record("events", "event_id", event_id, {"status": "Approved" if action == "approve" else "Rejected"})
    flash(f"Event request {'approved' if action == 'approve' else 'rejected'} successfully.", "success")
    return redirect(url_for("events"))


@app.route("/participations", methods=["GET", "POST"])
@login_required
def participations():
    user = get_current_user()
    default_festival = "ALL" if user["role"] == "host" else ""
    selected_festival = request.args.get("festival", default_festival)
    approved_events = visible_events_for(user)
    if selected_festival and selected_festival != "ALL":
        approved_events = [event for event in approved_events if event["parent_festival"] == selected_festival]
    elif user["role"] != "host":
        approved_events = []
    selected_event_id = request.args.get("event_id", type=int)
    if selected_event_id and not any(event["event_id"] == selected_event_id for event in approved_events):
        selected_event_id = None

    if request.method == "POST":
        event_id = request.form.get("event_id", type=int)
        participant_id = request.form.get("participant_id", type=int)
        if user["role"] != "host":
            participant = get_user_participant(user["user_id"])
            participant_id = participant["participant_id"] if participant else None
        if not participant_id or not event_id:
            flash("Please choose a valid participant and event.", "danger")
            return redirect(url_for("participations"))
        try:
            insert_record("event_participants", {"event_id": event_id, "participant_id": participant_id})
            flash("Participation registered successfully.", "success")
        except sqlite3.IntegrityError:
            flash("This participant is already registered for the event.", "danger")
        return redirect(url_for("participations", festival=request.form.get("festival_filter", default_festival)))

    connection = get_connection()
    if user["role"] == "host":
        registration_rows = connection.execute(
            """
            SELECT ep.registered_at, e.event_name, e.parent_festival, e.event_date, p.participant_name, p.registration_number
            FROM event_participants ep
            JOIN events e ON e.event_id = ep.event_id
            JOIN participants p ON p.participant_id = ep.participant_id
            ORDER BY ep.registered_at DESC
            """
        ).fetchall()
        if selected_event_id:
            all_participants = get_event_participants(selected_event_id)
        else:
            all_participants = []
    else:
        registration_rows = connection.execute(
            """
            SELECT ep.registered_at, e.event_name, e.parent_festival, e.event_date
            FROM event_participants ep
            JOIN participants p ON p.participant_id = ep.participant_id
            JOIN events e ON e.event_id = ep.event_id
            WHERE p.user_id = ?
            ORDER BY ep.registered_at DESC
            """,
            [user["user_id"]],
        ).fetchall()
        all_participants = []
    connection.close()
    registration_rows = [dict(row) for row in registration_rows]
    for row in registration_rows:
        row["event_date_label"] = format_date_label(row["event_date"])

    return render_template(
        "participations.html",
        active_page="participations",
        selected_festival=selected_festival,
        selected_event_id=selected_event_id,
        event_groups=events_grouped_by_festival(visible_events_for(user)),
        filtered_events=approved_events,
        registration_rows=registration_rows,
        all_participants=all_participants,
    )


@app.route("/participants")
@login_required
@host_required
def participants():
    selected_event_id = request.args.get("event_id", type=int)
    participant_rows = enrich_participants(fetch_table("participants", order_by="created_at", descending=True))
    connection = get_connection()
    registration_rows = connection.execute(
        """
        SELECT p.participant_id, e.parent_festival, e.event_name
        FROM event_participants ep
        JOIN participants p ON p.participant_id = ep.participant_id
        JOIN events e ON e.event_id = ep.event_id
        ORDER BY e.parent_festival, e.event_name
        """
    ).fetchall()
    connection.close()
    events_by_participant = defaultdict(list)
    for row in registration_rows:
        row = dict(row)
        events_by_participant[row["participant_id"]].append(f"{row['parent_festival']} - {row['event_name']}")
    for participant in participant_rows:
        linked_events = events_by_participant.get(participant["participant_id"], [])
        participant["selected_events"] = linked_events
        participant["selected_events_label"] = ", ".join(linked_events[:3]) if linked_events else "No events selected"
        if len(linked_events) > 3:
            participant["selected_events_label"] += f" +{len(linked_events) - 3} more"
    if selected_event_id:
        eligible_participant_ids = {
            row["participant_id"]
            for row in fetch_table("event_participants", where="event_id = ?", params=[selected_event_id])
        }
        participant_rows = [p for p in participant_rows if p["participant_id"] in eligible_participant_ids]
    host_events = enrich_events(fetch_table("events", order_by="event_date"))
    return render_template("participants.html", active_page="participants", participants=participant_rows, host_events=host_events, selected_event_id=selected_event_id)


@app.route("/analytics")
@login_required
def analytics():
    selected_festival = request.args.get("festival", "ALL")
    selected_chart = request.args.get("chart", "bar")
    payload = chart_payload(selected_festival)
    summary = {
        "total_events": len(payload["events"]),
        "total_registrations": sum(payload["popularity_counter"].values()),
        "selected_festival": selected_festival,
    }
    return render_template(
        "analytics.html",
        active_page="analytics",
        selected_festival=selected_festival,
        selected_chart=selected_chart,
        chart_types=CHART_TYPES,
        summary=summary,
    )


@app.route("/analytics/chart/<chart_type>.png")
@login_required
def analytics_chart(chart_type):
    festival_filter = request.args.get("festival", "ALL")
    chart_bytes = render_chart(chart_type, festival_filter)
    return Response(chart_bytes, mimetype="image/png")


def csv_response(filename_prefix, headers, rows):
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    response = Response(csv_buffer.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename_prefix}_{timestamp}.csv"
    return response


@app.route("/download/<scope>")
@login_required
def download_scope(scope):
    user = get_current_user()
    festival = request.args.get("festival", "ALL")
    event_id = request.args.get("event_id", type=int)
    connection = get_connection()

    if scope == "dashboard":
        if user["role"] != "host":
            flash("Only the host can download the full dashboard export.", "danger")
            return redirect(url_for("dashboard"))
        rows = connection.execute(
            """
            SELECT e.parent_festival, e.event_name, e.event_date, e.venue, e.status,
                   p.participant_name, p.registration_number, d.department_name, ep.registered_at
            FROM event_participants ep
            JOIN events e ON e.event_id = ep.event_id
            JOIN participants p ON p.participant_id = ep.participant_id
            LEFT JOIN departments d ON d.department_id = p.department_id
            ORDER BY e.parent_festival, e.event_name, p.participant_name
            """
        ).fetchall()
        connection.close()
        return csv_response(
            "dashboard_all_data",
            ["Festival", "Event", "Event Date", "Venue", "Status", "Participant", "Registration Number", "Department", "Registered At"],
            [list(dict(row).values()) for row in rows],
        )

    if scope == "events":
        query = "SELECT parent_festival, event_name, event_date, venue, organizer_name, status FROM events"
        params = []
        if festival != "ALL":
            query += " WHERE parent_festival = ?"
            params.append(festival)
        query += " ORDER BY parent_festival, event_date"
        rows = connection.execute(query, params).fetchall()
        connection.close()
        return csv_response("events_data", ["Festival", "Event", "Date", "Venue", "Organizer", "Status"], [list(dict(row).values()) for row in rows])

    if scope == "participations":
        if user["role"] == "host":
            query = """
                SELECT e.parent_festival, e.event_name, p.participant_name, p.registration_number, ep.registered_at
                FROM event_participants ep
                JOIN events e ON e.event_id = ep.event_id
                JOIN participants p ON p.participant_id = ep.participant_id
            """
            params = []
            if festival != "ALL":
                query += " WHERE e.parent_festival = ?"
                params.append(festival)
            query += " ORDER BY ep.registered_at DESC"
        else:
            query = """
                SELECT e.parent_festival, e.event_name, e.event_date, ep.registered_at
                FROM event_participants ep
                JOIN participants p ON p.participant_id = ep.participant_id
                JOIN events e ON e.event_id = ep.event_id
                WHERE p.user_id = ?
            """
            params = [user["user_id"]]
            if festival != "ALL":
                query += " AND e.parent_festival = ?"
                params.append(festival)
            query += " ORDER BY ep.registered_at DESC"
        rows = connection.execute(query, params).fetchall()
        connection.close()
        return csv_response("participations_data", list(dict(rows[0]).keys()) if rows else ["Data"], [list(dict(row).values()) for row in rows] or [["No data"]])

    if scope == "participants":
        if user["role"] != "host":
            flash("Only the host can download participant data.", "danger")
            return redirect(url_for("participants"))
        query = """
            SELECT p.participant_name, p.registration_number, d.department_name, p.year_of_study, p.phone
            FROM participants p
            LEFT JOIN departments d ON d.department_id = p.department_id
        """
        params = []
        if event_id:
            query += " JOIN event_participants ep ON ep.participant_id = p.participant_id WHERE ep.event_id = ?"
            params.append(event_id)
        query += " ORDER BY p.participant_name"
        rows = connection.execute(query, params).fetchall()
        connection.close()
        return csv_response("participants_data", ["Participant", "Registration Number", "Department", "Year", "Phone"], [list(dict(row).values()) for row in rows])

    if scope == "results":
        query = """
            SELECT e.parent_festival, e.event_name, p.participant_name, p.registration_number, r.rank_position, r.award_name
            FROM competition_results r
            JOIN events e ON e.event_id = r.event_id
            JOIN participants p ON p.participant_id = r.participant_id
        """
        params = []
        if event_id:
            query += " WHERE e.event_id = ?"
            params.append(event_id)
        query += " ORDER BY e.parent_festival, e.event_name, r.rank_position"
        rows = connection.execute(query, params).fetchall()
        connection.close()
        return csv_response("results_data", ["Festival", "Event", "Participant", "Registration Number", "Rank", "Award"], [list(dict(row).values()) for row in rows])

    if scope == "analytics":
        payload = chart_payload(festival)
        connection.close()
        rows = []
        for label, value in payload["popularity_counter"].most_common():
            rows.append([festival, label, value])
        return csv_response("analytics_summary", ["Festival Filter", "Event", "Registrations"], rows or [["No data", "", "0"]])

    connection.close()
    flash("Invalid download scope.", "danger")
    return redirect(url_for("dashboard"))


@app.route("/results", methods=["GET", "POST"])
@login_required
def results():
    user = get_current_user()
    if user["role"] != "host":
        return render_template("results_board.html", active_page="results", results_board=get_results_board(), page_effect="celebration")

    competition_events = [event for event in enrich_events(fetch_table("events", order_by="event_date")) if event["is_competition"]]
    selected_event_id = request.args.get("event_id", type=int) or request.form.get("event_id", type=int)
    selected_event = fetch_single("events", where="event_id = ?", params=[selected_event_id]) if selected_event_id else None
    participants_for_event = get_event_participants(selected_event_id) if selected_event_id else []

    if request.method == "POST" and selected_event_id:
        winner_ids = [
            request.form.get("first_place", type=int),
            request.form.get("second_place", type=int),
            request.form.get("third_place", type=int),
        ]
        picked = [winner_id for winner_id in winner_ids if winner_id]
        if len(set(picked)) != len(picked):
            flash("Please choose different participants for each winning position.", "danger")
            return redirect(url_for("results", event_id=selected_event_id))
        execute("DELETE FROM competition_results WHERE event_id = ?", [selected_event_id])
        awards = [(1, "Winner", 10000), (2, "Runner Up", 6000), (3, "Second Runner Up", 3000)]
        for (rank_position, award_name, prize_amount), participant_id in zip(awards, winner_ids):
            if participant_id:
                insert_record(
                    "competition_results",
                    {
                        "event_id": selected_event_id,
                        "participant_id": participant_id,
                        "rank_position": rank_position,
                        "award_name": award_name,
                        "prize_amount": prize_amount,
                        "remarks": "Updated by host",
                    },
                )
        flash("Results announced successfully.", "success")
        return redirect(url_for("results", event_id=selected_event_id))

    current_winners = fetch_table("competition_results", where="event_id = ?", params=[selected_event_id], order_by="rank_position") if selected_event_id else []
    winner_map = {row["rank_position"]: row["participant_id"] for row in current_winners}
    return render_template(
        "results.html",
        active_page="results",
        competition_events=competition_events,
        selected_event=selected_event,
        selected_event_id=selected_event_id,
        selected_participants=participants_for_event,
        winner_map=winner_map,
        results_board=get_results_board(),
        host_staff_accounts=fetch_table("portal_users", where="role IN ('faculty','organiser','coordinator')", order_by="created_at", descending=True),
        page_effect="celebration",
        show_create_account=False,
    )


@app.route("/profile")
@login_required
def profile():
    user = get_current_user()
    if user["role"] == "host":
        flash("Host account uses control panels instead of student profile history.", "danger")
        return redirect(url_for("dashboard"))
    participant = get_user_participant(user["user_id"])
    history_rows, wins_rows = get_user_history(user["user_id"])
    participant = enrich_participants([participant])[0] if participant else None
    return render_template("profile.html", active_page="profile", participant=participant, history_rows=history_rows, wins_rows=wins_rows)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


init_db()


if __name__ == "__main__":
    selected_port = find_available_port(os.getenv("PORT", "5001"))
    print(f"Starting College Event Portal on http://127.0.0.1:{selected_port}")
    app.run(debug=True, use_reloader=False, port=selected_port)
