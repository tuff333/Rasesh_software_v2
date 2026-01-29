import sqlite3
import json
from datetime import datetime
from flask import current_app


def get_conn():
    """Return a SQLite connection using the app's configured DB path."""
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def log_redaction(original, redacted, changes):
    """
    Log a redaction event into the database.
    Stores original filename, redacted filename, JSON changes, and timestamp.
    """

    timestamp = datetime.now().isoformat(timespec="seconds")

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO redactions (filename, redacted_file, changes, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (
                original,
                redacted,
                json.dumps(changes),
                timestamp
            )
        )
        conn.commit()
