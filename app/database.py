import sqlite3

DB_PATH = "database.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Vendors
    c.execute('''
    CREATE TABLE IF NOT EXISTS vendors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        gst_number TEXT,
        address TEXT,
        phone TEXT,
        email TEXT
    )
    ''')

    # GST Numbers
    c.execute('''
    CREATE TABLE IF NOT EXISTS gst_numbers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gst TEXT UNIQUE
    )
    ''')

    # Contacts
    c.execute('''
    CREATE TABLE IF NOT EXISTS contacts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        email TEXT,
        phone TEXT,
        company TEXT,
        position TEXT,
        address TEXT,
        notes TEXT
    )
    ''')

    # Invoices (simplified core)
    c.execute('''
    CREATE TABLE IF NOT EXISTS invoices(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        num TEXT,
        vendor_id INTEGER,
        date TEXT,
        subtotal REAL,
        tax REAL,
        total REAL,
        pdf_path TEXT,
        FOREIGN KEY(vendor_id) REFERENCES vendors(id)
    )
    ''')

    # Invoice items (single definition – duplicate removed)
    c.execute('''
    CREATE TABLE IF NOT EXISTS invoice_items(
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
    ''')

    # Manifests
    c.execute('''
    CREATE TABLE IF NOT EXISTS manifests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        num TEXT,
        date TEXT,
        carrier TEXT,
        delivery TEXT,
        ship_from TEXT,
        ship_to TEXT,
        contact TEXT,
        weight REAL,
        pdf_path TEXT
    )
    ''')

    # Manifest items
    c.execute('''
    CREATE TABLE IF NOT EXISTS manifest_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        manifest_id INTEGER,
        item TEXT,
        lot TEXT,
        weight REAL,
        FOREIGN KEY(manifest_id) REFERENCES manifests(id)
    )
    ''')

    # Redactor preview
    c.execute('''
    CREATE TABLE IF NOT EXISTS redaction_preview(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        page INTEGER,
        x REAL,
        y REAL,
        width REAL,
        height REAL,
        type TEXT,
        text TEXT,
        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Redactor workspace
    c.execute('''
    CREATE TABLE IF NOT EXISTS open_documents(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        display_name TEXT,
        active INTEGER DEFAULT 0,
        opened TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Redaction history
    c.execute('''
    CREATE TABLE IF NOT EXISTS redaction_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fname TEXT,
        orig TEXT,
        redacted TEXT,
        changes TEXT,
        ver INTEGER,
        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Settings table (used by app.services.settings)
    c.execute('''
    CREATE TABLE IF NOT EXISTS settings(
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')

    conn.commit()
    conn.close()
