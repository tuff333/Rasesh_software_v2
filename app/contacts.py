from flask import (
    Blueprint, render_template, request, redirect,
    url_for, current_app, send_file, jsonify
)
import sqlite3
import os
from werkzeug.utils import secure_filename
import xlsxwriter
from datetime import datetime
from io import BytesIO

contacts_bp = Blueprint("contacts", __name__, url_prefix="/contacts")


def get_conn():
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_upload_folder():
    base = os.path.join(current_app.root_path, "uploads", "contacts")
    os.makedirs(base, exist_ok=True)
    return base


# -------------------------
# TAG HELPERS
# -------------------------
def get_tags_for_contact(contact_id):
    with get_conn() as conn:
        c = conn.cursor()
        rows = c.execute("""
            SELECT t.name
            FROM contact_tags t
            JOIN contact_tag_map m ON m.tag_id = t.id
            WHERE m.contact_id = ?
            ORDER BY t.name
        """, (contact_id,)).fetchall()
    return [r["name"] for r in rows]


def set_tags_for_contact(contact_id, tags_csv):
    tags = [t.strip() for t in (tags_csv or "").split(",") if t.strip()]
    with get_conn() as conn:
        c = conn.cursor()
        # Clear existing
        c.execute("DELETE FROM contact_tag_map WHERE contact_id=?", (contact_id,))
        for tag in tags:
            # Ensure tag exists
            c.execute("INSERT OR IGNORE INTO contact_tags(name) VALUES (?)", (tag,))
            tag_row = c.execute("SELECT id FROM contact_tags WHERE name=?", (tag,)).fetchone()
            if tag_row:
                c.execute(
                    "INSERT OR IGNORE INTO contact_tag_map(contact_id, tag_id) VALUES (?, ?)",
                    (contact_id, tag_row["id"])
                )
        conn.commit()


# -------------------------
# NOTES HELPERS
# -------------------------
def get_notes_for_contact(contact_id):
    with get_conn() as conn:
        c = conn.cursor()
        rows = c.execute("""
            SELECT id, contact_id, timestamp, note_text
            FROM contact_notes
            WHERE contact_id=?
            ORDER BY timestamp DESC, id DESC
        """, (contact_id,)).fetchall()
    return rows


# ------------------------------------------------------------
# CONTACT LIST
# ------------------------------------------------------------
@contacts_bp.route("/")
def contacts_list():
    search = request.args.get("search", "").strip()

    with get_conn() as conn:
        c = conn.cursor()

        if search:
            rows = c.execute(
                """
                SELECT id, first_name_contact, last_name_contact,
                       email_contact, phone_contact, company_contact, position_contact
                FROM contacts
                WHERE first_name_contact LIKE ?
                   OR last_name_contact LIKE ?
                   OR company_contact LIKE ?
                ORDER BY id DESC
                """,
                (f"%{search}%", f"%{search}%", f"%{search}%")
            ).fetchall()
        else:
            rows = c.execute(
                """
                SELECT id, first_name_contact, last_name_contact,
                       email_contact, phone_contact, company_contact, position_contact
                FROM contacts
                ORDER BY id DESC
                """
            ).fetchall()

    contacts = []
    for r in rows:
        tags = get_tags_for_contact(r["id"])
        contacts.append(
            {
                "id": r["id"],
                "first": r["first_name_contact"] or "",
                "last": r["last_name_contact"] or "",
                "email": r["email_contact"] or "",
                "phone": r["phone_contact"] or "",
                "company": r["company_contact"] or "",
                "position": r["position_contact"] or "",
                "tags": tags,
            }
        )

    return render_template("contacts/list.html", contacts=contacts, search=search)


# ------------------------------------------------------------
# ADD CONTACT
# ------------------------------------------------------------
@contacts_bp.route("/add", methods=["GET", "POST"])
def contacts_add():
    if request.method == "POST":
        return save_contact_to_db()
    return render_template("contacts/form.html", contact=None, tags_csv="")


# ------------------------------------------------------------
# EDIT CONTACT
# ------------------------------------------------------------
@contacts_bp.route("/edit/<int:id>", methods=["GET", "POST"])
def contacts_edit(id):
    with get_conn() as conn:
        c = conn.cursor()
        contact = c.execute("SELECT * FROM contacts WHERE id=?", (id,)).fetchone()

    if not contact:
        return "Contact not found", 404

    if request.method == "POST":
        return save_contact_to_db(id=id)

    tags = ",".join(get_tags_for_contact(id))
    return render_template("contacts/form.html", contact=contact, tags_csv=tags)


# ------------------------------------------------------------
# SAVE CONTACT (ADD + EDIT)
# ------------------------------------------------------------
def save_contact_to_db(id=None):
    first = request.form.get("first_name", "").strip()
    last = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    company = request.form.get("company", "").strip()
    position = request.form.get("position", "").strip()
    address = request.form.get("address", "").strip()
    notes = request.form.get("notes", "").strip()
    website = request.form.get("website", "").strip()
    tags_csv = request.form.get("tags", "").strip()

    upload_folder = get_upload_folder()

    def save_file(field_name, prefix):
        file = request.files.get(field_name)
        if not file or file.filename == "":
            return None
        filename = secure_filename(file.filename)
        final_name = f"{prefix}_{filename}"
        path = os.path.join(upload_folder, final_name)
        file.save(path)
        return os.path.join("uploads", "contacts", final_name)

    business_card_front = save_file("business_card_front", f"{first}_{last}_front")
    business_card_back = save_file("business_card_back", f"{first}_{last}_back")
    face_image = save_file("face_image", f"{first}_{last}_face")
    company_logo = save_file("company_logo", f"{company}_logo")

    with get_conn() as conn:
        c = conn.cursor()
        if id is None:
            c.execute(
                """
                INSERT INTO contacts(
                    first_name_contact, last_name_contact, email_contact, phone_contact,
                    company_contact, position_contact, address_contact, notes_contact,
                    website_contact, business_card_front_contact, business_card_back_contact,
                    face_image_contact, company_logo_contact
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    first, last, email, phone, company, position, address, notes,
                    website, business_card_front, business_card_back,
                    face_image, company_logo
                )
            )
            new_id = c.lastrowid
            conn.commit()
            set_tags_for_contact(new_id, tags_csv)
        else:
            c.execute(
                """
                UPDATE contacts SET
                    first_name_contact=?, last_name_contact=?, email_contact=?, phone_contact=?,
                    company_contact=?, position_contact=?, address_contact=?, notes_contact=?,
                    website_contact=?,
                    business_card_front_contact=COALESCE(?, business_card_front_contact),
                    business_card_back_contact=COALESCE(?, business_card_back_contact),
                    face_image_contact=COALESCE(?, face_image_contact),
                    company_logo_contact=COALESCE(?, company_logo_contact)
                WHERE id=?
                """,
                (
                    first, last, email, phone, company, position, address, notes,
                    website,
                    business_card_front, business_card_back,
                    face_image, company_logo,
                    id
                )
            )
            conn.commit()
            set_tags_for_contact(id, tags_csv)

    return redirect(url_for("contacts.contacts_list"))


# ------------------------------------------------------------
# DELETE CONTACT
# ------------------------------------------------------------
@contacts_bp.route("/delete/<int:id>", methods=["POST"])
def contacts_delete(id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM contact_notes WHERE contact_id=?", (id,))
        c.execute("DELETE FROM contact_tag_map WHERE contact_id=?", (id,))
        c.execute("DELETE FROM contacts WHERE id=?", (id,))
        conn.commit()
    return redirect(url_for("contacts.contacts_list"))


# ------------------------------------------------------------
# FULL VIEW CONTACT
# ------------------------------------------------------------
@contacts_bp.route("/view/<int:id>")
def view_contact(id):
    with get_conn() as conn:
        c = conn.cursor()
        contact = c.execute("SELECT * FROM contacts WHERE id=?", (id,)).fetchone()

    if not contact:
        return "Contact not found", 404

    tags = get_tags_for_contact(id)
    notes = get_notes_for_contact(id)

    return render_template("contacts/view.html", contact=contact, tags=tags, notes=notes)


from flask import (
    Blueprint, render_template, request, redirect,
    url_for, current_app, send_file, jsonify, flash
)
import sqlite3
import os
from werkzeug.utils import secure_filename
import xlsxwriter
from datetime import datetime, date
from io import BytesIO
import csv

contacts_bp = Blueprint("contacts", __name__, url_prefix="/contacts")


def get_conn():
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_contact_extra_tables(conn)
    return conn


def get_upload_folder():
    base = os.path.join(current_app.root_path, "uploads", "contacts")
    os.makedirs(base, exist_ok=True)
    return base

# ------------------------------------------------------------
# AVATAR COLOR HELPER
# ------------------------------------------------------------
import hashlib

def avatar_color(name):
    """Generate a consistent color from a name."""
    if not name:
        return "#6c757d"  # fallback gray
    h = hashlib.md5(name.encode()).hexdigest()
    r = int(h[:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return f"rgb({r},{g},{b})"


# ------------------------------------------------------------
# DB: ENSURE EXTRA TABLES (ADD-ONLY, SAFE)
# ------------------------------------------------------------
def ensure_contact_extra_tables(conn: sqlite3.Connection):
    c = conn.cursor()

    # Tags (already used, but ensure)
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
            UNIQUE(contact_id, tag_id)
        )
    """)

    # Notes (already used, but ensure)
    c.execute("""
        CREATE TABLE IF NOT EXISTS contact_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            note_text TEXT NOT NULL
        )
    """)

    # Files
    c.execute("""
        CREATE TABLE IF NOT EXISTS contact_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            uploaded_at TEXT NOT NULL
        )
    """)

    # Reminders
    c.execute("""
        CREATE TABLE IF NOT EXISTS contact_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open'
        )
    """)

    # Email templates
    c.execute("""
        CREATE TABLE IF NOT EXISTS contact_email_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL
        )
    """)

    # Activity log (for enhanced timeline)
    c.execute("""
        CREATE TABLE IF NOT EXISTS contact_activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT NOT NULL
        )
    """)

    # Merge log
    c.execute("""
        CREATE TABLE IF NOT EXISTS contact_merge_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            primary_contact_id INTEGER NOT NULL,
            merged_contact_id INTEGER NOT NULL,
            merged_at TEXT NOT NULL
        )
    """)

    conn.commit()


# -------------------------
# TAG HELPERS
# -------------------------
def get_tags_for_contact(contact_id):
    with get_conn() as conn:
        c = conn.cursor()
        rows = c.execute("""
            SELECT t.name
            FROM contact_tags t
            JOIN contact_tag_map m ON m.tag_id = t.id
            WHERE m.contact_id = ?
            ORDER BY t.name
        """, (contact_id,)).fetchall()
    return [r["name"] for r in rows]


def set_tags_for_contact(contact_id, tags_csv):
    tags = [t.strip() for t in (tags_csv or "").split(",") if t.strip()]
    with get_conn() as conn:
        c = conn.cursor()
        # Clear existing
        c.execute("DELETE FROM contact_tag_map WHERE contact_id=?", (contact_id,))
        for tag in tags:
            # Ensure tag exists
            c.execute("INSERT OR IGNORE INTO contact_tags(name) VALUES (?)", (tag,))
            tag_row = c.execute("SELECT id FROM contact_tags WHERE name=?", (tag,)).fetchone()
            if tag_row:
                c.execute(
                    "INSERT OR IGNORE INTO contact_tag_map(contact_id, tag_id) VALUES (?, ?)",
                    (contact_id, tag_row["id"])
                )
        conn.commit()


def get_all_tags():
    with get_conn() as conn:
        c = conn.cursor()
        rows = c.execute("SELECT name FROM contact_tags ORDER BY name").fetchall()
    return [r["name"] for r in rows]


# -------------------------
# NOTES HELPERS
# -------------------------
def get_notes_for_contact(contact_id):
    with get_conn() as conn:
        c = conn.cursor()
        rows = c.execute("""
            SELECT id, contact_id, timestamp, note_text
            FROM contact_notes
            WHERE contact_id=?
            ORDER BY timestamp DESC, id DESC
        """, (contact_id,)).fetchall()
    return rows


def log_activity(contact_id, type_, description):
    ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO contact_activity_log(contact_id, timestamp, type, description)
            VALUES (?, ?, ? ,?)
        """, (contact_id, ts, type_, description))
        conn.commit()


def get_activity_for_contact(contact_id):
    with get_conn() as conn:
        c = conn.cursor()
        rows = c.execute("""
            SELECT id, contact_id, timestamp, type, description
            FROM contact_activity_log
            WHERE contact_id=?
            ORDER BY timestamp DESC, id DESC
        """, (contact_id,)).fetchall()
    return rows

# ------------------------------------------------------------
# CONTACT LIST (WITH TAG FILTERING)
# ------------------------------------------------------------
@contacts_bp.route("/")
def contacts_list():
    search = request.args.get("search", "").strip()
    tag_filter = request.args.get("tag", "").strip()

    with get_conn() as conn:
        c = conn.cursor()

        base_query = """
            SELECT id, first_name_contact, last_name_contact,
                   email_contact, phone_contact, company_contact, position_contact,
                   status, pipeline_stage
            FROM contacts
        """
        params = []

        where_clauses = []
        if search:
            where_clauses.append("""
                (first_name_contact LIKE ?
                 OR last_name_contact LIKE ?
                 OR company_contact LIKE ?)
            """)
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        if tag_filter:
            base_query += """
                JOIN contact_tag_map m ON m.contact_id = contacts.id
                JOIN contact_tags t ON t.id = m.tag_id
            """
            where_clauses.append("t.name = ?")
            params.append(tag_filter)

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        base_query += " ORDER BY contacts.id DESC"

        rows = c.execute(base_query, tuple(params)).fetchall()

    contacts = []
    for r in rows:
        tags = get_tags_for_contact(r["id"])

        # SAFE ACCESS — sqlite3.Row does NOT support .get()
        status = r["status"] if "status" in r.keys() else "active"
        stage = r["pipeline_stage"] if "pipeline_stage" in r.keys() else "new"

        contacts.append(
            {
                "id": r["id"],
                "first": r["first_name_contact"] or "",
                "last": r["last_name_contact"] or "",
                "email": r["email_contact"] or "",
                "phone": r["phone_contact"] or "",
                "company": r["company_contact"] or "",
                "position": r["position_contact"] or "",
                "tags": tags,
                "status": status,
                "stage": stage,
                "avatar_color": avatar_color(f"{r['first_name_contact']} {r['last_name_contact']}")
            }
        )

    all_tags = get_all_tags()

    return render_template(
        "contacts/list.html",
        contacts=contacts,
        search=search,
        tag_filter=tag_filter,
        all_tags=all_tags
    )

# ------------------------------------------------------------
# ADD CONTACT
# ------------------------------------------------------------
@contacts_bp.route("/add", methods=["GET", "POST"])
def contacts_add():
    if request.method == "POST":
        return save_contact_to_db()
    return render_template("contacts/form.html", contact=None, tags_csv="")


# ------------------------------------------------------------
# EDIT CONTACT
# ------------------------------------------------------------
@contacts_bp.route("/edit/<int:id>", methods=["GET", "POST"])
def contacts_edit(id):
    with get_conn() as conn:
        c = conn.cursor()
        contact = c.execute("SELECT * FROM contacts WHERE id=?", (id,)).fetchone()

    if not contact:
        return "Contact not found", 404

    if request.method == "POST":
        return save_contact_to_db(id=id)

    tags = ",".join(get_tags_for_contact(id))
    return render_template("contacts/form.html", contact=contact, tags_csv=tags)


# ------------------------------------------------------------
# SAVE CONTACT (ADD + EDIT)
# ------------------------------------------------------------
def save_contact_to_db(id=None):
    first = request.form.get("first_name", "").strip()
    last = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    company = request.form.get("company", "").strip()
    position = request.form.get("position", "").strip()
    address = request.form.get("address", "").strip()
    notes = request.form.get("notes", "").strip()
    website = request.form.get("website", "").strip()
    tags_csv = request.form.get("tags", "").strip()

    upload_folder = get_upload_folder()

    def save_file(field_name, prefix):
        file = request.files.get(field_name)
        if not file or file.filename == "":
            return None
        filename = secure_filename(file.filename)
        final_name = f"{prefix}_{filename}"
        path = os.path.join(upload_folder, final_name)
        file.save(path)
        return os.path.join("uploads", "contacts", final_name)

    business_card_front = save_file("business_card_front", f"{first}_{last}_front")
    business_card_back = save_file("business_card_back", f"{first}_{last}_back")
    face_image = save_file("face_image", f"{first}_{last}_face")
    company_logo = save_file("company_logo", f"{company}_logo")

    with get_conn() as conn:
        c = conn.cursor()
        if id is None:
            c.execute(
                """
                INSERT INTO contacts(
                    first_name_contact, last_name_contact, email_contact, phone_contact,
                    company_contact, position_contact, address_contact, notes_contact,
                    website_contact, business_card_front_contact, business_card_back_contact,
                    face_image_contact, company_logo_contact
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    first, last, email, phone, company, position, address, notes,
                    website, business_card_front, business_card_back,
                    face_image, company_logo
                )
            )
            new_id = c.lastrowid
            conn.commit()
            set_tags_for_contact(new_id, tags_csv)
            log_activity(new_id, "create", "Contact created")
        else:
            c.execute(
                """
                UPDATE contacts SET
                    first_name_contact=?, last_name_contact=?, email_contact=?, phone_contact=?,
                    company_contact=?, position_contact=?, address_contact=?, notes_contact=?,
                    website_contact=?,
                    business_card_front_contact=COALESCE(?, business_card_front_contact),
                    business_card_back_contact=COALESCE(?, business_card_back_contact),
                    face_image_contact=COALESCE(?, face_image_contact),
                    company_logo_contact=COALESCE(?, company_logo_contact)
                WHERE id=?
                """,
                (
                    first, last, email, phone, company, position, address, notes,
                    website,
                    business_card_front, business_card_back,
                    face_image, company_logo,
                    id
                )
            )
            conn.commit()
            set_tags_for_contact(id, tags_csv)
            log_activity(id, "update", "Contact updated")

    return redirect(url_for("contacts.contacts_list"))

# ------------------------------------------------------------
# DELETE CONTACT
# ------------------------------------------------------------
@contacts_bp.route("/delete/<int:id>", methods=["POST"])
def contacts_delete(id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM contact_notes WHERE contact_id=?", (id,))
        c.execute("DELETE FROM contact_tag_map WHERE contact_id=?", (id,))
        c.execute("DELETE FROM contact_files WHERE contact_id=?", (id,))
        c.execute("DELETE FROM contact_reminders WHERE contact_id=?", (id,))
        c.execute("DELETE FROM contact_activity_log WHERE contact_id=?", (id,))
        c.execute("DELETE FROM contacts WHERE id=?", (id,))
        conn.commit()
    return redirect(url_for("contacts.contacts_list"))

# ------------------------------------------------------------
# UPDATE CONTACT STATUS
# ------------------------------------------------------------
@contacts_bp.route("/status/<int:id>", methods=["POST"])
def update_status(id):
    new_status = request.form.get("status", "").strip()
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE contacts SET status=? WHERE id=?", (new_status, id))
        conn.commit()
    log_activity(id, "status", f"Status changed to {new_status}")
    return redirect(url_for("contacts.view_contact", id=id))

# ------------------------------------------------------------
# UPDATE PIPELINE STAGE
# ------------------------------------------------------------
@contacts_bp.route("/pipeline/<int:id>", methods=["POST"])
def update_pipeline(id):
    new_stage = request.form.get("stage", "").strip()
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE contacts SET pipeline_stage=? WHERE id=?", (new_stage, id))
        conn.commit()
    log_activity(id, "pipeline", f"Moved to stage {new_stage}")
    return redirect(url_for("contacts.view_contact", id=id))

# ------------------------------------------------------------
# FULL VIEW CONTACT
# ------------------------------------------------------------
@contacts_bp.route("/view/<int:id>")
def view_contact(id):
    with get_conn() as conn:
        c = conn.cursor()
        contact = c.execute("SELECT * FROM contacts WHERE id=?", (id,)).fetchone()

        files = c.execute("""
            SELECT id, filename, stored_path, uploaded_at
            FROM contact_files
            WHERE contact_id=?
            ORDER BY uploaded_at DESC, id DESC
        """, (id,)).fetchall()

        reminders = c.execute("""
            SELECT id, title, due_date, status
            FROM contact_reminders
            WHERE contact_id=?
            ORDER BY due_date ASC, id ASC
        """, (id,)).fetchall()

    if not contact:
        return "Contact not found", 404

    tags = get_tags_for_contact(id)
    notes = get_notes_for_contact(id)
    activity = get_activity_for_contact(id)

    return render_template(
        "contacts/view.html",
        contact=contact,
        tags=tags,
        notes=notes,
        files=files,
        reminders=reminders,
        activity=activity
    )


# ------------------------------------------------------------
# MODAL VIEW CONTACT (AJAX HTML)
# ------------------------------------------------------------
@contacts_bp.route("/view_modal/<int:id>")
def view_contact_modal(id):
    with get_conn() as conn:
        c = conn.cursor()
        contact = c.execute("SELECT * FROM contacts WHERE id=?", (id,)).fetchone()

    if not contact:
        return "Contact not found", 404

    tags = get_tags_for_contact(id)
    notes = get_notes_for_contact(id)

    return render_template("contacts/view_modal.html", contact=contact, tags=tags, notes=notes)


# ------------------------------------------------------------
# ADD NOTE
# ------------------------------------------------------------
@contacts_bp.route("/<int:id>/notes/add", methods=["POST"])
def add_note(id):
    note_text = request.form.get("note_text", "").strip()
    if not note_text:
        return redirect(url_for("contacts.view_contact", id=id))

    ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO contact_notes(contact_id, timestamp, note_text) VALUES (?, ?, ?)",
            (id, ts, note_text)
        )
        conn.commit()

    log_activity(id, "note", f"Note added: {note_text[:80]}")
    return redirect(url_for("contacts.view_contact", id=id))


# ------------------------------------------------------------
# DELETE NOTE
# ------------------------------------------------------------
@contacts_bp.route("/notes/delete/<int:note_id>", methods=["POST"])
def delete_note(note_id):
    with get_conn() as conn:
        c = conn.cursor()
        row = c.execute(
            "SELECT contact_id, note_text FROM contact_notes WHERE id=?", (note_id,)
        ).fetchone()
        if not row:
            return "Note not found", 404
        contact_id = row["contact_id"]
        note_text = row["note_text"]
        c.execute("DELETE FROM contact_notes WHERE id=?", (note_id,))
        conn.commit()

    log_activity(contact_id, "note_delete", f"Note deleted: {note_text[:80]}")
    return redirect(url_for("contacts.view_contact", id=contact_id))


# ------------------------------------------------------------
# FILES: UPLOAD / DELETE / DOWNLOAD
# ------------------------------------------------------------
@contacts_bp.route("/<int:id>/files/upload", methods=["POST"])
def upload_file(id):
    file = request.files.get("file")
    if not file or file.filename == "":
        return redirect(url_for("contacts.view_contact", id=id))

    upload_folder = get_upload_folder()
    filename = secure_filename(file.filename)
    final_name = f"file_{id}_{filename}"
    path = os.path.join(upload_folder, final_name)
    file.save(path)

    stored_path = os.path.join("uploads", "contacts", final_name)
    ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO contact_files(contact_id, filename, stored_path, uploaded_at)
            VALUES (?, ?, ?, ?)
        """, (id, filename, stored_path, ts))
        conn.commit()

    log_activity(id, "file_upload", f"File uploaded: {filename}")
    return redirect(url_for("contacts.view_contact", id=id))


@contacts_bp.route("/files/delete/<int:file_id>", methods=["POST"])
def delete_file(file_id):
    with get_conn() as conn:
        c = conn.cursor()
        row = c.execute("""
            SELECT contact_id, filename, stored_path
            FROM contact_files
            WHERE id=?
        """, (file_id,)).fetchone()
        if not row:
            return "File not found", 404
        contact_id = row["contact_id"]
        filename = row["filename"]
        stored_path = row["stored_path"]

        c.execute("DELETE FROM contact_files WHERE id=?", (file_id,))
        conn.commit()

    abs_path = os.path.join(current_app.root_path, stored_path)
    if os.path.exists(abs_path):
        try:
            os.remove(abs_path)
        except OSError:
            pass

    log_activity(contact_id, "file_delete", f"File deleted: {filename}")
    return redirect(url_for("contacts.view_contact", id=contact_id))


@contacts_bp.route("/files/download/<int:file_id>")
def download_file(file_id):
    with get_conn() as conn:
        c = conn.cursor()
        row = c.execute("""
            SELECT filename, stored_path
            FROM contact_files
            WHERE id=?
        """, (file_id,)).fetchone()
        if not row:
            return "File not found", 404

    abs_path = os.path.join(current_app.root_path, row["stored_path"])
    if not os.path.exists(abs_path):
        return "File missing on disk", 404

    return send_file(abs_path, as_attachment=True, download_name=row["filename"])


# ------------------------------------------------------------
# REMINDERS
# ------------------------------------------------------------
@contacts_bp.route("/<int:id>/reminders/add", methods=["POST"])
def add_reminder(id):
    title = request.form.get("reminder_title", "").strip()
    due_date = request.form.get("reminder_due_date", "").strip()
    if not title or not due_date:
        return redirect(url_for("contacts.view_contact", id=id))

    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO contact_reminders(contact_id, title, due_date, status)
            VALUES (?, ?, ?, 'open')
        """, (id, title, due_date))
        conn.commit()

    log_activity(id, "reminder_add", f"Reminder added: {title} ({due_date})")
    return redirect(url_for("contacts.view_contact", id=id))


@contacts_bp.route("/reminders/complete/<int:reminder_id>", methods=["POST"])
def complete_reminder(reminder_id):
    with get_conn() as conn:
        c = conn.cursor()
        row = c.execute("""
            SELECT contact_id, title
            FROM contact_reminders
            WHERE id=?
        """, (reminder_id,)).fetchone()
        if not row:
            return "Reminder not found", 404
        contact_id = row["contact_id"]
        title = row["title"]

        c.execute("""
            UPDATE contact_reminders
            SET status='done'
            WHERE id=?
        """, (reminder_id,))
        conn.commit()

    log_activity(contact_id, "reminder_done", f"Reminder completed: {title}")
    return redirect(url_for("contacts.view_contact", id=contact_id))


@contacts_bp.route("/reminders/delete/<int:reminder_id>", methods=["POST"])
def delete_reminder(reminder_id):
    with get_conn() as conn:
        c = conn.cursor()
        row = c.execute("""
            SELECT contact_id, title
            FROM contact_reminders
            WHERE id=?
        """, (reminder_id,)).fetchone()
        if not row:
            return "Reminder not found", 404
        contact_id = row["contact_id"]
        title = row["title"]

        c.execute("DELETE FROM contact_reminders WHERE id=?", (reminder_id,))
        conn.commit()

    log_activity(contact_id, "reminder_delete", f"Reminder deleted: {title}")
    return redirect(url_for("contacts.view_contact", id=contact_id))


# ------------------------------------------------------------
# EXPORT SINGLE CONTACT (XLSX)
# ------------------------------------------------------------
@contacts_bp.route("/export/<int:id>")
def export_contact(id):
    with get_conn() as conn:
        c = conn.cursor()
        contact = c.execute("SELECT * FROM contacts WHERE id=?", (id,)).fetchone()

    if not contact:
        return "Contact not found", 404

    export_dir = os.path.join(get_upload_folder(), "exports")
    os.makedirs(export_dir, exist_ok=True)

    filename = f"contact_{id}.xlsx"
    filepath = os.path.join(export_dir, filename)

    workbook = xlsxwriter.Workbook(filepath)
    sheet = workbook.add_worksheet("Contact")

    row = 0
    for key in contact.keys():
        sheet.write(row, 0, key)
        sheet.write(row, 1, contact[key])
        row += 1

    workbook.close()

    return send_file(filepath, as_attachment=True)

# ------------------------------------------------------------
# EXPORT ALL CONTACTS (XLSX)
# ------------------------------------------------------------
@contacts_bp.route("/export_all")
def export_all_contacts():
    with get_conn() as conn:
        c = conn.cursor()
        rows = c.execute("SELECT * FROM contacts ORDER BY id DESC").fetchall()

    export_dir = os.path.join(get_upload_folder(), "exports")
    os.makedirs(export_dir, exist_ok=True)

    filename = f"all_contacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(export_dir, filename)

    workbook = xlsxwriter.Workbook(filepath)
    sheet = workbook.add_worksheet("Contacts")

    headers = rows[0].keys() if rows else []
    for col, h in enumerate(headers):
        sheet.write(0, col, h)

    for row_idx, r in enumerate(rows, start=1):
        for col_idx, h in enumerate(headers):
            sheet.write(row_idx, col_idx, r[h])

    workbook.close()

    return send_file(filepath, as_attachment=True)


# ------------------------------------------------------------
# VCARD EXPORT
# ------------------------------------------------------------
@contacts_bp.route("/vcard/<int:id>")
def export_vcard(id):
    with get_conn() as conn:
        c = conn.cursor()
        contact = c.execute("SELECT * FROM contacts WHERE id=?", (id,)).fetchone()

    if not contact:
        return "Contact not found", 404

    first = contact["first_name_contact"] or ""
    last = contact["last_name_contact"] or ""
    full_name = (first + " " + last).strip()
    email = contact["email_contact"] or ""
    phone = contact["phone_contact"] or ""
    company = contact["company_contact"] or ""
    title = contact["position_contact"] or ""
    website = contact["website_contact"] or ""
    address = contact["address_contact"] or ""

    vcard = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{last};{first};;;",
        f"FN:{full_name}",
        f"ORG:{company}",
        f"TITLE:{title}",
        f"TEL;TYPE=WORK,VOICE:{phone}",
        f"EMAIL;TYPE=PREF,INTERNET:{email}",
        f"URL:{website}",
        f"ADR;TYPE=WORK:;;{address};;;;",
        "END:VCARD",
    ]
    data = "\r\n".join(vcard)

    buf = BytesIO(data.encode("utf-8"))
    buf.seek(0)
    filename = f"{full_name or 'contact'}.vcf"

    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype="text/vcard"
    )


# ------------------------------------------------------------
# ICS MEETING EXPORT
# ------------------------------------------------------------
@contacts_bp.route("/ics/<int:id>")
def export_ics(id):
    with get_conn() as conn:
        c = conn.cursor()
        contact = c.execute("SELECT * FROM contacts WHERE id=?", (id,)).fetchone()

    if not contact:
        return "Contact not found", 404

    first = contact["first_name_contact"] or ""
    last = contact["last_name_contact"] or ""
    full_name = (first + " " + last).strip()
    email = contact["email_contact"] or ""
    now = datetime.utcnow()
    dtstamp = now.strftime("%Y%m%dT%H%M%SZ")
    dtstart = now.strftime("%Y%m%dT%H%M%SZ")
    dtend = (now.replace(hour=now.hour + 1)).strftime("%Y%m%dT%H%M%SZ")

    ics = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Rasesh CRM//EN",
        "BEGIN:VEVENT",
        f"UID:{id}-{dtstamp}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{dtstart}",
        f"DTEND:{dtend}",
        f"SUMMARY:Meeting with {full_name}",
        f"DESCRIPTION:Auto-generated meeting with {full_name} ({email})",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    data = "\r\n".join(ics)

    buf = BytesIO(data.encode("utf-8"))
    buf.seek(0)
    filename = f"meeting_{full_name or 'contact'}.ics"

    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype="text/calendar"
    )


# ------------------------------------------------------------
# CSV IMPORT (BULK CONTACT UPLOAD)
# ------------------------------------------------------------
@contacts_bp.route("/import", methods=["GET", "POST"])
def import_contacts():
    if request.method == "GET":
        return render_template("contacts/import.html")

    file = request.files.get("file")
    if not file or file.filename == "":
        flash("No file selected", "danger")
        return redirect(url_for("contacts.import_contacts"))

    # Expect UTF-8 CSV with header row
    stream = file.stream.read().decode("utf-8", errors="ignore").splitlines()
    reader = csv.DictReader(stream)

    created = 0
    for row in reader:
        first = (row.get("first_name") or "").strip()
        last = (row.get("last_name") or "").strip()
        email = (row.get("email") or "").strip()
        phone = (row.get("phone") or "").strip()
        company = (row.get("company") or "").strip()
        position = (row.get("position") or "").strip()
        address = (row.get("address") or "").strip()
        notes = (row.get("notes") or "").strip()
        website = (row.get("website") or "").strip()
        tags_csv = (row.get("tags") or "").strip()

        if not (first or last or email or phone):
            continue

        with get_conn() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO contacts(
                    first_name_contact, last_name_contact, email_contact, phone_contact,
                    company_contact, position_contact, address_contact, notes_contact,
                    website_contact
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                first, last, email, phone, company, position, address, notes, website
            ))
            new_id = c.lastrowid
            conn.commit()
            set_tags_for_contact(new_id, tags_csv)
            log_activity(new_id, "import", "Contact imported from CSV")
            created += 1

    flash(f"Imported {created} contacts from CSV.", "success")
    return redirect(url_for("contacts.contacts_list"))

# ------------------------------------------------------------
# MERGE DUPLICATES (BASIC BY EMAIL/PHONE)
# ------------------------------------------------------------
@contacts_bp.route("/duplicates")
def duplicates():
    with get_conn() as conn:
        c = conn.cursor()
        # Find duplicates by email or phone
        dup_rows = c.execute("""
            SELECT email_contact AS key, GROUP_CONCAT(id) AS ids
            FROM contacts
            WHERE email_contact IS NOT NULL AND email_contact <> ''
            GROUP BY email_contact
            HAVING COUNT(*) > 1
        """).fetchall()

        dup_rows_phone = c.execute("""
            SELECT phone_contact AS key, GROUP_CONCAT(id) AS ids
            FROM contacts
            WHERE phone_contact IS NOT NULL AND phone_contact <> ''
            GROUP BY phone_contact
            HAVING COUNT(*) > 1
        """).fetchall()

    email_dups = []
    for r in dup_rows:
        ids = [int(x) for x in r["ids"].split(",")]
        email_dups.append({"key": r["key"], "ids": ids})

    phone_dups = []
    for r in dup_rows_phone:
        ids = [int(x) for x in r["ids"].split(",")]
        phone_dups.append({"key": r["key"], "ids": ids})

    return render_template(
        "contacts/duplicates.html",
        email_dups=email_dups,
        phone_dups=phone_dups
    )


@contacts_bp.route("/merge", methods=["POST"])
def merge_contacts():
    primary_id = int(request.form.get("primary_id", "0") or "0")
    merge_ids_raw = request.form.get("merge_ids", "")  # comma-separated
    if not primary_id or not merge_ids_raw:
        return redirect(url_for("contacts.duplicates"))

    merge_ids = [int(x) for x in merge_ids_raw.split(",") if x.strip()]
    merge_ids = [mid for mid in merge_ids if mid != primary_id]

    if not merge_ids:
        return redirect(url_for("contacts.duplicates"))

    with get_conn() as conn:
        c = conn.cursor()

        primary = c.execute("SELECT * FROM contacts WHERE id=?", (primary_id,)).fetchone()
        if not primary:
            return redirect(url_for("contacts.duplicates"))

        # Merge notes, tags, files, reminders, activity
        for mid in merge_ids:
            # Move notes
            c.execute("""
                UPDATE contact_notes
                SET contact_id=?
                WHERE contact_id=?
            """, (primary_id, mid))

            # Move tags
            c.execute("""
                UPDATE OR IGNORE contact_tag_map
                SET contact_id=?
                WHERE contact_id=?
            """, (primary_id, mid))

            # Move files
            c.execute("""
                UPDATE contact_files
                SET contact_id=?
                WHERE contact_id=?
            """, (primary_id, mid))

            # Move reminders
            c.execute("""
                UPDATE contact_reminders
                SET contact_id=?
                WHERE contact_id=?
            """, (primary_id, mid))

            # Move activity
            c.execute("""
                UPDATE contact_activity_log
                SET contact_id=?
                WHERE contact_id=?
            """, (primary_id, mid))

            # Log merge
            ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            c.execute("""
                INSERT INTO contact_merge_log(primary_contact_id, merged_contact_id, merged_at)
                VALUES (?, ?, ?)
            """, (primary_id, mid, ts))

            # Delete merged contact
            c.execute("DELETE FROM contacts WHERE id=?", (mid,))

        conn.commit()

    log_activity(primary_id, "merge", f"Merged contacts: {merge_ids}")
    return redirect(url_for("contacts.view_contact", id=primary_id))

# ------------------------------------------------------------
# PIPELINE BOARD (KANBAN)
# ------------------------------------------------------------
@contacts_bp.route("/pipeline")
def pipeline_board():
    with get_conn() as conn:
        c = conn.cursor()
        rows = c.execute("SELECT * FROM contacts ORDER BY id DESC").fetchall()

    stages = ["new", "contacted", "qualified", "proposal", "won", "lost"]
    board = {s: [] for s in stages}

    for r in rows:
        full_name = f"{r['first_name_contact']} {r['last_name_contact']}".strip()
        board[r["pipeline_stage"]].append({
            "id": r["id"],
            "name": full_name,
            "company": r["company_contact"],
            "status": r["status"],
            "avatar_color": avatar_color(full_name)
        })

    return render_template("contacts/pipeline.html", board=board)

# ------------------------------------------------------------
# COMPANY DIRECTORY VIEW
# ------------------------------------------------------------
@contacts_bp.route("/companies")
def companies():
    with get_conn() as conn:
        c = conn.cursor()
        rows = c.execute("""
            SELECT
                COALESCE(company_contact, '') AS company,
                id, first_name_contact, last_name_contact,
                email_contact, phone_contact, position_contact
            FROM contacts
            ORDER BY company_contact, last_name_contact, first_name_contact
        """).fetchall()

    companies_map = {}
    for r in rows:
        company = r["company"] or "(No Company)"
        companies_map.setdefault(company, [])
        companies_map[company].append(r)

    # Sort companies by name
    sorted_companies = sorted(companies_map.items(), key=lambda x: x[0].lower())

    return render_template(
        "contacts/companies.html",
        companies=sorted_companies
    )

# ------------------------------------------------------------
# CONTACT ANALYTICS DASHBOARD
# ------------------------------------------------------------
@contacts_bp.route("/analytics")
def analytics():
    with get_conn() as conn:
        c = conn.cursor()

        # Contacts by company
        by_company = c.execute("""
            SELECT COALESCE(company_contact, '') AS company, COUNT(*) AS count
            FROM contacts
            GROUP BY COALESCE(company_contact, '')
            ORDER BY count DESC
        """).fetchall()

        # Contacts by tag
        by_tag = c.execute("""
            SELECT t.name AS tag, COUNT(*) AS count
            FROM contact_tags t
            JOIN contact_tag_map m ON m.tag_id = t.id
            GROUP BY t.name
            ORDER BY count DESC
        """).fetchall()

        # Contacts added per month (approx by id / created not stored; fallback: count only)
        total_contacts = c.execute("SELECT COUNT(*) AS cnt FROM contacts").fetchone()["cnt"]

        # Notes count
        notes_count = c.execute("SELECT COUNT(*) AS cnt FROM contact_notes").fetchone()["cnt"]

        # Reminders open/done
        reminders_open = c.execute("""
            SELECT COUNT(*) AS cnt FROM contact_reminders WHERE status='open'
        """).fetchone()["cnt"]
        reminders_done = c.execute("""
            SELECT COUNT(*) AS cnt FROM contact_reminders WHERE status='done'
        """).fetchone()["cnt"]

    return render_template(
        "contacts/analytics.html",
        by_company=by_company,
        by_tag=by_tag,
        total_contacts=total_contacts,
        notes_count=notes_count,
        reminders_open=reminders_open,
        reminders_done=reminders_done
    )


# ------------------------------------------------------------
# EMAIL TEMPLATES (BACKEND ONLY, UI LATER)
# ------------------------------------------------------------
@contacts_bp.route("/email_templates")
def email_templates_list():
    with get_conn() as conn:
        c = conn.cursor()
        rows = c.execute("""
            SELECT id, name, subject, body
            FROM contact_email_templates
            ORDER BY name
        """).fetchall()
    return render_template("contacts/email_templates.html", templates=rows)


@contacts_bp.route("/email_templates/add", methods=["GET", "POST"])
def email_templates_add():
    if request.method == "GET":
        return render_template("contacts/email_templates_form.html", template=None)

    name = request.form.get("name", "").strip()
    subject = request.form.get("subject", "").strip()
    body = request.form.get("body", "").strip()

    if not name or not subject or not body:
        return render_template("contacts/email_templates_form.html", template=None, error="All fields required")

    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO contact_email_templates(name, subject, body)
            VALUES (?, ?, ?)
        """, (name, subject, body))
        conn.commit()

    return redirect(url_for("contacts.email_templates_list"))


@contacts_bp.route("/email_templates/edit/<int:id>", methods=["GET", "POST"])
def email_templates_edit(id):
    with get_conn() as conn:
        c = conn.cursor()
        template = c.execute("""
            SELECT id, name, subject, body
            FROM contact_email_templates
            WHERE id=?
        """, (id,)).fetchone()

    if not template:
        return "Template not found", 404

    if request.method == "GET":
        return render_template("contacts/email_templates_form.html", template=template)

    name = request.form.get("name", "").strip()
    subject = request.form.get("subject", "").strip()
    body = request.form.get("body", "").strip()

    if not name or not subject or not body:
        return render_template("contacts/email_templates_form.html", template=template, error="All fields required")

    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE contact_email_templates
            SET name=?, subject=?, body=?
            WHERE id=?
        """, (name, subject, body, id))
        conn.commit()

    return redirect(url_for("contacts.email_templates_list"))


@contacts_bp.route("/email_templates/delete/<int:id>", methods=["POST"])
def email_templates_delete(id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM contact_email_templates WHERE id=?", (id,))
        conn.commit()
    return redirect(url_for("contacts.email_templates_list"))

# ------------------------------------------------------------
# USE EMAIL TEMPLATE → OPEN EMAIL INSERT PAGE
# ------------------------------------------------------------
@contacts_bp.route("/email_templates/use/<int:template_id>/<int:contact_id>")
def use_email_template(template_id, contact_id):
    with get_conn() as conn:
        c = conn.cursor()

        template = c.execute("""
            SELECT id, name, subject, body
            FROM contact_email_templates
            WHERE id=?
        """, (template_id,)).fetchone()

        contact = c.execute("""
            SELECT *
            FROM contacts
            WHERE id=?
        """, (contact_id,)).fetchone()

    if not template or not contact:
        return "Template or contact not found", 404

    # Fill merge fields
    filled_body = template["body"]
    filled_body = filled_body.replace("{{first}}", contact["first_name_contact"] or "")
    filled_body = filled_body.replace("{{last}}", contact["last_name_contact"] or "")
    filled_body = filled_body.replace("{{company}}", contact["company_contact"] or "")
    filled_body = filled_body.replace("{{email}}", contact["email_contact"] or "")
    filled_body = filled_body.replace("{{phone}}", contact["phone_contact"] or "")

    return render_template(
        "contacts/email_insert.html",
        contact=contact,
        template=template,
        filled_body=filled_body
    )
