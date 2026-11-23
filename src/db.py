
import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "events.db"


def create_table():
    """Create the events table if it doesn't exist."""
    with sqlite3.connect(DB_NAME) as conn:
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


def save_event(driver_id, vehicle_id, event_type, duration_s, severity):
    """Save a new event with the current timestamp."""
    timestamp = datetime.now().isoformat(timespec="seconds")

    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            INSERT INTO events (
                timestamp,
                driver_id,
                vehicle_id,
                event_type,
                duration_s,
                severity
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            driver_id,
            vehicle_id,
            event_type,
            duration_s,
            severity
        ))


def get_events():
    """Retrieve all events as a pandas DataFrame."""
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM events ORDER BY timestamp DESC",
            conn
        )

    return df


# Create the table when this module is imported.
create_table()
