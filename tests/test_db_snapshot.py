# Checks the snapshot column upgrade and snapshot saving.
# Run from the project folder: python tests/test_db_snapshot.py [scratch_folder]

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

# Always test the local SQLite file, never the shared Supabase database.
os.environ["DATABASE_URL"] = ""

sys.path.insert(0, "src")
import db
import detector

scratch = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp())
db.DB_NAME = scratch / "old_events.db"
db.DB_NAME.unlink(missing_ok=True)

# An old database: events table without the snapshot column, one row in it.
with sqlite3.connect(db.DB_NAME) as conn:
    conn.execute("""
        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            driver_id TEXT NOT NULL,
            vehicle_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            duration_s REAL NOT NULL,
            severity TEXT NOT NULL
        )
    """)
    conn.execute(
        "INSERT INTO events (timestamp, driver_id, vehicle_id, event_type, duration_s, severity) "
        "VALUES ('2026-11-20T10:00:00', 'DRIVER_001', 'VEHICLE_001', 'YAWN', 1.5, 'LOW')"
    )

# Running it twice must be safe (the dashboard and detector both call it).
db.create_table()
db.create_table()
db.save_event("DRIVER_002", "VEHICLE_002", "PHONE", 2.3, "HIGH", snapshot="data/snapshots/x.jpg")

rows = db.get_events().sort_values("id")
assert len(rows) == 2
assert rows.iloc[0]["event_type"] == "YAWN" and pd.isna(rows.iloc[0]["snapshot"])
assert rows.iloc[1]["snapshot"] == "data/snapshots/x.jpg"

# Detector: a saved event writes a ~480 px JPEG and stores its relative path.
detector.ROOT = scratch
detector.SNAPSHOT_FOLDER = scratch / "data" / "snapshots"

detector.snapshots["PHONE"] = np.full((720, 1280, 3), 128, np.uint8)
assert detector.finish_event("PHONE", 0.0, 2.0) is not None
assert "PHONE" not in detector.snapshots

saved = db.get_events().sort_values("id").iloc[-1]["snapshot"]
assert saved.startswith("data/snapshots/") and saved.endswith("_PHONE.jpg"), saved
picture = detector.cv2.imread(str(scratch / saved))
assert picture.shape[1] == 480

# A broken picture must not stop the event from being saved.
detector.snapshots["YAWN"] = np.zeros((0, 0, 3), np.uint8)
assert detector.finish_event("YAWN", 0.0, 2.0) is not None
assert len(db.get_events()) == 4

# No picture at all (alert never fired) is fine too.
assert detector.finish_event("LOOK_AWAY", 0.0, 3.0) is not None
assert len(db.get_events()) == 5

print("test_db_snapshot: all checks passed")
