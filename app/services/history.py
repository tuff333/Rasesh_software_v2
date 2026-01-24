import sqlite3
import json
from app.database import DB_PATH

def log_redaction(original, redacted, changes):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO redaction_history(fname, orig, redacted, changes, ver) VALUES(?,?,?,?,1)",
            (original, original, redacted, json.dumps(changes))
        )
        conn.commit()
