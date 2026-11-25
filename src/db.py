
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_NAME = ROOT / "data" / "events.db"


def create_table():
    """Create the webcam and driving events tables if they don't exist."""

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


def save_event(driver_id, vehicle_id, event_type, duration_s, severity):
    """Save a webcam event with the current timestamp."""

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
    """Retrieve all webcam events as a pandas DataFrame."""

    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM events ORDER BY timestamp DESC",
            conn
        )

    return df


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

    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
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

    with sqlite3.connect(DB_NAME) as conn:
        conn.executemany("""
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
        """, rows)


def get_driving_events():
    """Retrieve all driving behaviour events as a pandas DataFrame."""

    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM driving_events ORDER BY timestamp DESC",
            conn
        )

    return df


# Create both tables when this module is imported.
create_table()
