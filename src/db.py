
import os
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_NAME = ROOT / "data" / "events.db"

# Read KEY=value lines from .env (python-dotenv is not installed).
# A variable that is already set (e.g. Streamlit Cloud secrets) wins.
ENV_FILE = ROOT / ".env"

if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and not line.lstrip().startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

# DATABASE_URL set   -> shared Supabase Postgres (laptop and cloud see the same events).
# DATABASE_URL empty -> local SQLite file data/events.db, exactly as before.
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRES = bool(DATABASE_URL)


def connect():
    """Open the database. Use it as: with connect() as conn: ..."""

    if USE_POSTGRES:
        import psycopg  # only needed in Postgres mode
        return psycopg.connect(DATABASE_URL)

    return sqlite3.connect(DB_NAME)


def run(conn, query, params=()):
    """Run one query. Postgres writes its placeholders as %s instead of ?."""

    if USE_POSTGRES:
        query = query.replace("?", "%s")

    return conn.execute(query, params)


def to_dataframe(cursor):
    """Turn query results into a DataFrame with the column names."""

    columns = [column[0] for column in cursor.description]
    return pd.DataFrame(cursor.fetchall(), columns=columns)


def create_table():
    """Create the webcam and driving events tables if they don't exist."""

    if USE_POSTGRES:
        create_postgres_tables()
        return

    DB_NAME.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_NAME) as conn:

        # Existing webcam events table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                driver_id TEXT NOT NULL,
                vehicle_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                duration_s REAL NOT NULL,
                severity TEXT NOT NULL
            )
        """)

        # Older databases were made before snapshots existed.
        # Add the column without touching the saved rows.
        columns = [row[1] for row in conn.execute("PRAGMA table_info(events)")]

        if "snapshot" not in columns:
            conn.execute("ALTER TABLE events ADD COLUMN snapshot TEXT")

        # Separate driving behaviour events table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS driving_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                driver_id TEXT NOT NULL,
                vehicle_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                measured_value REAL NOT NULL,
                threshold_value REAL NOT NULL,
                severity TEXT NOT NULL
            )
        """)


def create_postgres_tables():
    """Same tables in Postgres, plus snapshot_jpeg so the cloud can show the picture."""

    with connect() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                timestamp TEXT NOT NULL,
                driver_id TEXT NOT NULL,
                vehicle_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                duration_s DOUBLE PRECISION NOT NULL,
                severity TEXT NOT NULL,
                snapshot TEXT,
                snapshot_jpeg BYTEA
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS driving_events (
                id SERIAL PRIMARY KEY,
                timestamp TEXT NOT NULL,
                driver_id TEXT NOT NULL,
                vehicle_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                measured_value DOUBLE PRECISION NOT NULL,
                threshold_value DOUBLE PRECISION NOT NULL,
                severity TEXT NOT NULL
            )
        """)


def save_event(driver_id, vehicle_id, event_type, duration_s, severity, timestamp=None, snapshot=None):
    """
    Save a webcam event. Uses the current time unless a timestamp is given.
    snapshot is the picture path (relative to the project folder), or None.
    """

    if timestamp is None:
        timestamp = datetime.now().isoformat(timespec="seconds")

    if USE_POSTGRES:

        # The cloud dashboard cannot see this laptop's files, so store the picture itself.
        picture = ROOT / snapshot if snapshot else None
        jpeg = picture.read_bytes() if picture and picture.exists() else None

        with connect() as conn:
            run(conn, """
                INSERT INTO events (
                    timestamp, driver_id, vehicle_id, event_type,
                    duration_s, severity, snapshot, snapshot_jpeg
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, driver_id, vehicle_id, event_type, duration_s, severity, snapshot, jpeg))

        return

    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            INSERT INTO events (
                timestamp,
                driver_id,
                vehicle_id,
                event_type,
                duration_s,
                severity,
                snapshot
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            driver_id,
            vehicle_id,
            event_type,
            duration_s,
            severity,
            snapshot
        ))


def get_events():
    """Retrieve all webcam events as a pandas DataFrame."""

    # Named columns, not *: the picture bytes stay out (the live panel polls every 2 s).
    with connect() as conn:
        df = to_dataframe(run(conn, """
            SELECT id, timestamp, driver_id, vehicle_id, event_type,
                   duration_s, severity, snapshot
            FROM events
            ORDER BY timestamp DESC
        """))

    return df


def get_latest_snapshot():
    """
    Newest event that has a picture, as a dict:
    {"jpeg": bytes, "event_type": ..., "timestamp": ...}. None if there is none.
    """

    picture_column = "snapshot_jpeg" if USE_POSTGRES else "snapshot"

    with connect() as conn:
        row = run(conn, f"""
            SELECT {picture_column}, event_type, timestamp
            FROM events
            WHERE {picture_column} IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 1
        """).fetchone()

    if row is None:
        return None

    picture, event_type, timestamp = row

    if not USE_POSTGRES:

        # Local mode stores only the file path, so read the picture from disk.
        path = ROOT / picture

        if not path.exists():
            return None

        picture = path.read_bytes()

    return {"jpeg": bytes(picture), "event_type": event_type, "timestamp": timestamp}


def save_driving_event(
    driver_id,
    vehicle_id,
    event_type,
    measured_value,
    threshold_value,
    severity,
    timestamp=None,
):
    """Save one driving behaviour event."""

    if timestamp is None:
        timestamp = datetime.now().isoformat(timespec="seconds")

    with connect() as conn:
        run(conn, """
            INSERT INTO driving_events (
                timestamp,
                driver_id,
                vehicle_id,
                event_type,
                measured_value,
                threshold_value,
                severity
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            driver_id,
            vehicle_id,
            event_type,
            measured_value,
            threshold_value,
            severity
        ))


def save_driving_events(events):
    """Save multiple driving behaviour events in one transaction."""

    rows = []

    for event in events:
        timestamp = event.get("timestamp")

        if timestamp is None:
            timestamp = datetime.now().isoformat(timespec="seconds")

        rows.append((
            timestamp,
            event["driver_id"],
            event["vehicle_id"],
            event["event_type"],
            event["measured_value"],
            event["threshold_value"],
            event["severity"],
        ))

    placeholders = ", ".join(["%s" if USE_POSTGRES else "?"] * 7)

    with connect() as conn:
        conn.cursor().executemany(f"""
            INSERT INTO driving_events (
                timestamp,
                driver_id,
                vehicle_id,
                event_type,
                measured_value,
                threshold_value,
                severity
            )
            VALUES ({placeholders})
        """, rows)


def get_driving_events():
    """Retrieve all driving behaviour events as a pandas DataFrame."""

    with connect() as conn:
        df = to_dataframe(run(conn, "SELECT * FROM driving_events ORDER BY timestamp DESC"))

    return df


# Create both tables when this module is imported.
create_table()
