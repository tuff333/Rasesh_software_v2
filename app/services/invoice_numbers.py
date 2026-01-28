import sqlite3
from flask import current_app


def get_conn():
    """Return a SQLite connection using the app's configured DB path."""
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def next_invoice_number(invoice_type="Invoice"):
    """
    Generate the next invoice/estimate/quote number.
    invoice_type: "Invoice", "Estimate", "Quote"
    """

    prefix_map = {
        "Invoice": "INV",
        "Estimate": "EST",
        "Quote": "QUO"
    }

    prefix = prefix_map.get(invoice_type, "INV")

    with get_conn() as conn:
        row = conn.execute(
            "SELECT num FROM invoices WHERE invoice_type=? ORDER BY id DESC LIMIT 1",
            (invoice_type,)
        ).fetchone()

    # No previous invoices of this type
    if not row or not row["num"]:
        return f"{prefix}-0001"

    # Extract numeric part
    try:
        last_num = int(row["num"].split("-")[-1])
    except Exception:
        last_num = 0

    new_num = last_num + 1
    return f"{prefix}-{new_num:04d}"
