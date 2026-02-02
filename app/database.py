import sqlite3
import os
from flask import current_app


def get_conn():
    """Return a SQLite connection using the app's configured DB path."""
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all required tables if they do not exist and align schemas."""
    with get_conn() as conn:
        c = conn.cursor()

        # -------------------------
        # INVOICES
        # -------------------------
        c.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                num TEXT,
                date TEXT,
                vendor_id INTEGER,
                invoice_type TEXT,
                comments TEXT,
                terms_conditions TEXT,
                sig_id INTEGER,
                ship_cost REAL,
                tax_rate REAL,
                tax REAL,
                subtotal REAL,
                total REAL,
                pdf TEXT,
                gst_number TEXT,
                ship_method TEXT,
                ship_terms TEXT,
                delivery_date TEXT,
                template TEXT,
                FOREIGN KEY(vendor_id) REFERENCES vendors(id)
            )
        """)

        # -------------------------
        # INVOICE ITEMS
        # -------------------------
        c.execute("""
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER,
                lot_number TEXT,
                item TEXT,
                qty REAL,
                units TEXT,
                unit_price REAL,
                line_total REAL,
                FOREIGN KEY(invoice_id) REFERENCES invoices(id)
            )
        """)

        # -------------------------
        # MANIFESTS
        # -------------------------
        c.execute("""
            CREATE TABLE IF NOT EXISTS manifests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                num TEXT,
                date TEXT,
                carrier TEXT,
                delivery TEXT,
                ship_from TEXT,
                ship_to TEXT,
                contact_name TEXT,
                ship_method TEXT,
                sig_id INTEGER,
                total_weight REAL,
                pdf TEXT
            )
        """)

        # -------------------------
        # MANIFEST ITEMS
        # -------------------------
        c.execute("""
            CREATE TABLE IF NOT EXISTS manifest_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manifest_id INTEGER,
                item TEXT,
                lot TEXT,
                weight REAL,
                FOREIGN KEY(manifest_id) REFERENCES manifests(id)
            )
        """)

        # -------------------------
        # CONTACTS
        # -------------------------
        c.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                first_name_contact TEXT,
                last_name_contact TEXT,
                email_contact TEXT,
                phone_contact TEXT,
                company_contact TEXT,
                position_contact TEXT,
                address_contact TEXT,
                notes_contact TEXT,
                website_contact TEXT,
                business_card_front_contact TEXT,
                business_card_back_contact TEXT,
                face_image_contact TEXT,
                company_logo_contact TEXT
            )
        """)

        # CONTACT MIGRATIONS
        existing_contact_cols = {
            row[1] for row in c.execute("PRAGMA table_info(contacts);").fetchall()
        }

        required_contact_cols = {
            "first_name_contact": "TEXT",
            "last_name_contact": "TEXT",
            "email_contact": "TEXT",
            "phone_contact": "TEXT",
            "company_contact": "TEXT",
            "position_contact": "TEXT",
            "address_contact": "TEXT",
            "notes_contact": "TEXT",
            "website_contact": "TEXT",
            "business_card_front_contact": "TEXT",
            "business_card_back_contact": "TEXT",
            "face_image_contact": "TEXT",
            "company_logo_contact": "TEXT",
        }

        for col, col_type in required_contact_cols.items():
            if col not in existing_contact_cols:
                c.execute(f"ALTER TABLE contacts ADD COLUMN {col} {col_type};")

        # -------------------------
        # CONTACT NOTES
        # -------------------------
        c.execute("""
            CREATE TABLE IF NOT EXISTS contact_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                note_text TEXT NOT NULL,
                FOREIGN KEY(contact_id) REFERENCES contacts(id)
            )
        """)

        # -------------------------
        # CONTACT TAGS
        # -------------------------
        c.execute("""
            CREATE TABLE IF NOT EXISTS contact_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS contact_tag_map (
                contact_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (contact_id, tag_id),
                FOREIGN KEY(contact_id) REFERENCES contacts(id),
                FOREIGN KEY(tag_id) REFERENCES contact_tags(id)
            )
        """)

        # -------------------------
        # VENDORS
        # -------------------------
        c.execute("""
            CREATE TABLE IF NOT EXISTS vendors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                gst_number TEXT,
                address TEXT,
                phone TEXT,
                email TEXT
            )
        """)

        # -------------------------
        # GST
        # -------------------------
        c.execute("""
            CREATE TABLE IF NOT EXISTS gst (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gst_number TEXT,
                description TEXT,
                is_default INTEGER DEFAULT 0
            )
        """)

        # -------------------------
        # ITEMS
        # -------------------------
        c.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                default_units TEXT,
                default_price REAL
            )
        """)

        # -------------------------
        # INVOICE SEQUENCES
        # -------------------------
        c.execute("""
            CREATE TABLE IF NOT EXISTS invoice_sequences (
                prefix TEXT PRIMARY KEY,
                last_number INTEGER
            )
        """)

        # -------------------------
        # SIGNATURES
        # -------------------------
        c.execute("""
            CREATE TABLE IF NOT EXISTS signatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                position TEXT,
                filename TEXT NOT NULL,
                is_default INTEGER DEFAULT 0
            )
        """)

        # -------------------------
        # REDACTIONS (UPDATED)
        # -------------------------
        c.execute("""
            CREATE TABLE IF NOT EXISTS redactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                output_file TEXT,
                changes TEXT,
                timestamp TEXT
            )
        """)

        existing_redaction_cols = {
            row[1] for row in c.execute("PRAGMA table_info(redactions);").fetchall()
        }

        required_redaction_cols = {
            "output_file": "TEXT",
            "changes": "TEXT"
        }

        for col, col_type in required_redaction_cols.items():
            if col not in existing_redaction_cols:
                c.execute(f"ALTER TABLE redactions ADD COLUMN {col} {col_type};")

        # -------------------------
        # REDACTION TEMPLATES
        # -------------------------
        c.execute("""
            CREATE TABLE IF NOT EXISTS redaction_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                company TEXT,
                doc_type TEXT,
                boxes_json TEXT NOT NULL,
                created_at TEXT
            )
        """)

        # -------------------------
        # REDACTION TEMPLATE VERSIONS (NEW)
        # -------------------------
        c.execute("""
            CREATE TABLE IF NOT EXISTS redaction_template_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                version INTEGER NOT NULL,
                name TEXT,
                company TEXT,
                doc_type TEXT,
                boxes_json TEXT NOT NULL,
                created_at TEXT,
                FOREIGN KEY(template_id) REFERENCES redaction_templates(id)
            )
        """)

        # -------------------------
        # INVOICE MIGRATIONS
        # -------------------------
        existing_cols = {
            row[1] for row in c.execute("PRAGMA table_info(invoices);").fetchall()
        }

        required_invoice_cols = {
            "gst_number": "TEXT",
            "ship_method": "TEXT",
            "ship_terms": "TEXT",
            "delivery_date": "TEXT",
            "template": "TEXT"
        }

        for col, col_type in required_invoice_cols.items():
            if col not in existing_cols:
                c.execute(f"ALTER TABLE invoices ADD COLUMN {col} {col_type};")

        conn.commit()
