import sqlite3
from app.database import DB_PATH

def open_document(filename, display_name):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        row = c.execute(
            "SELECT id FROM open_documents WHERE filename=?",
            (filename,)
        ).fetchone()

        if row:
            c.execute("UPDATE open_documents SET active=0")
            c.execute("UPDATE open_documents SET active=1 WHERE filename=?", (filename,))
        else:
            c.execute("UPDATE open_documents SET active=0")
            c.execute(
                "INSERT INTO open_documents(filename, display_name, active) VALUES(?,?,1)",
                (filename, display_name)
            )

        conn.commit()


def list_documents():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT id, filename, display_name, active FROM open_documents ORDER BY opened ASC"
        ).fetchall()

    return [
        {
            "id": r[0],
            "filename": r[1],
            "display_name": r[2],
            "active": bool(r[3])
        }
        for r in rows
    ]


def set_active(filename):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE open_documents SET active=0")
        conn.execute("UPDATE open_documents SET active=1 WHERE filename=?", (filename,))
        conn.commit()


def close_document(filename):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM open_documents WHERE filename=?", (filename,))
        conn.execute("DELETE FROM redaction_preview WHERE filename=?", (filename,))
        conn.commit()
