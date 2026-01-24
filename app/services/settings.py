import sqlite3
from app.database import DB_PATH
import os

DEFAULT_PATHS = {
    "output_redaction": "output/redaction",
    "output_invoice": "output/invoice",
    "output_manifest": "output/manifest"
}

def get_setting(key):
    """Return a setting value or None."""
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else None


def set_setting(key, value):
    """Insert or update a setting."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )
        conn.commit()


def get_output_path(category):
    """
    category = 'redaction', 'invoice', 'manifest'
    Returns the configured path or default path.
    Ensures the folder exists.
    """
    key = f"output_{category}"
    path = get_setting(key)

    if not path:
        # Use default
        path = DEFAULT_PATHS[key]

    # Ensure folder exists
    os.makedirs(path, exist_ok=True)
    return path
