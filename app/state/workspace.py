import sqlite3
from datetime import datetime
from flask import current_app


def get_conn():
    """Return a SQLite connection using the app's configured DB path."""
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def open_document(filename, display_name):
    """
    Open or activate a document in the workspace.
    If already open → activate it.
    If new → insert it and activate it.
    """

    timestamp = datetime.now().isoformat(timespec="seconds")

    with get_conn() as conn:
        c = conn.cursor()

        # Ensure table exists
        c.execute("""
            CREATE TABLE IF NOT EXISTS open_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                display_name TEXT,
                active INTEGER,
                opened TEXT
            )
        """)

        # Deactivate all
        c.execute("UPDATE open_documents SET active=0")

        # Check if already open
        row = c.execute(
            "SELECT id FROM open_documents WHERE filename=?",
            (filename,)
        ).fetchone()

        if row:
            # Activate existing
            c.execute(
                "UPDATE open_documents SET active=1 WHERE filename=?",
                (filename,)
            )
        else:
            # Insert new
            c.execute(
                """
                INSERT INTO open_documents(filename, display_name, active, opened)
                VALUES (?, ?, 1, ?)
                """,
                (filename, display_name, timestamp)
            )

        conn.commit()


def list_documents():
    """Return all open documents in workspace."""

    with get_conn() as conn:
        c = conn.cursor()

        # Ensure table exists
        c.execute("""
            CREATE TABLE IF NOT EXISTS open_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                display_name TEXT,
                active INTEGER,
                opened TEXT
            )
        """)

        rows = c.execute(
            "SELECT id, filename, display_name, active FROM open_documents ORDER BY opened ASC"
        ).fetchall()

    return [
        {
            "id": r["id"],
            "filename": r["filename"],
            "display_name": r["display_name"],
            "active": bool(r["active"])
        }
        for r in rows
    ]


def set_active(filename):
    """Set a document as active."""

    with get_conn() as conn:
        c = conn.cursor()

        # Ensure table exists
        c.execute("""
            CREATE TABLE IF NOT EXISTS open_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                display_name TEXT,
                active INTEGER,
                opened TEXT
            )
        """)

        c.execute("UPDATE open_documents SET active=0")
        c.execute("UPDATE open_documents SET active=1 WHERE filename=?", (filename,))
        conn.commit()


def close_document(filename):
    """Close a document and remove its preview data."""

    with get_conn() as conn:
        c = conn.cursor()

        # Ensure tables exist
        c.execute("""
            CREATE TABLE IF NOT EXISTS open_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                display_name TEXT,
                active INTEGER,
                opened TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS redaction_preview (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                page INTEGER,
                preview_path TEXT
            )
        """)

        # Remove document
        c.execute("DELETE FROM open_documents WHERE filename=?", (filename,))

        # Remove previews
        c.execute("DELETE FROM redaction_preview WHERE filename=?", (filename,))

        conn.commit()
