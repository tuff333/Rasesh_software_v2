import sqlite3
from app.database import DB_PATH

def next_invoice_number():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    row = cur.execute("SELECT num FROM invoices ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()

    if not row or not row[0]:
        return "INV-0001"

    last = row[0].replace("INV-", "")
    try:
        num = int(last) + 1
    except:
        num = 1

    return f"INV-{num:04d}"
