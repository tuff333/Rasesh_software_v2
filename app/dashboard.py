import sqlite3
import os
from flask import current_app
from datetime import datetime, timedelta


def get_conn():
    """Return a SQLite connection using the app's configured DB path."""
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_dashboard_stats():
    """Return all dashboard statistics."""
    conn = get_conn()
    c = conn.cursor()

    # -----------------------------
    # TOTAL COUNTS
    # -----------------------------
    try:
        c.execute("SELECT COUNT(*) AS c FROM vendors")
        total_vendors = c.fetchone()["c"]
    except:
        total_vendors = 0

    try:
        c.execute("SELECT COUNT(*) AS c FROM contacts")
        total_contacts = c.fetchone()["c"]
    except:
        total_contacts = 0

    try:
        c.execute("SELECT COUNT(*) AS c FROM invoices")
        total_invoices = c.fetchone()["c"]
    except:
        total_invoices = 0

    try:
        c.execute("SELECT COUNT(*) AS c FROM manifests")
        total_manifests = c.fetchone()["c"]
    except:
        total_manifests = 0

    # -----------------------------
    # REVENUE TOTAL
    # -----------------------------
    try:
        c.execute("SELECT SUM(total) AS s FROM invoices")
        total_revenue = c.fetchone()["s"] or 0
    except:
        total_revenue = 0

    # -----------------------------
    # REVENUE LAST 30 DAYS
    # -----------------------------
    try:
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        c.execute(
            "SELECT SUM(total) AS s FROM invoices WHERE date >= ?",
            (cutoff,)
        )
        monthly_revenue = c.fetchone()["s"] or 0
    except:
        monthly_revenue = 0

    # -----------------------------
    # RECENT INVOICES (limit 10)
    # -----------------------------
    try:
        c.execute("""
            SELECT invoices.id,
                   invoices.num,
                   invoices.date,
                   invoices.total,
                   invoices.invoice_type,
                   invoices.pdf,
                   vendors.name AS vendor
            FROM invoices
            LEFT JOIN vendors ON vendors.id = invoices.vendor_id
            ORDER BY invoices.id DESC
            LIMIT 10
        """)
        recent_invoices = c.fetchall()
    except:
        recent_invoices = []

    conn.close()

    return {
        "total_vendors": total_vendors,
        "total_contacts": total_contacts,
        "total_invoices": total_invoices,
        "total_manifests": total_manifests,
        "total_revenue": total_revenue,
        "monthly_revenue": monthly_revenue,
        "recent_invoices": recent_invoices,
    }


def get_recent_invoices():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        SELECT invoices.id,
               invoices.num,
               invoices.date,
               invoices.total,
               invoices.invoice_type,
               invoices.pdf,
               vendors.name AS vendor
        FROM invoices
        LEFT JOIN vendors ON vendors.id = invoices.vendor_id
        ORDER BY invoices.id DESC
        LIMIT 10
    """)

    rows = c.fetchall()
    conn.close()
    return rows
