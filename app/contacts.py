from flask import Blueprint, render_template, request, redirect, url_for, current_app
import sqlite3

contacts_bp = Blueprint("contacts", __name__, url_prefix="/contacts")


def get_conn():
    """Return a SQLite connection using the app's configured DB path."""
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ------------------------------------------------------------
# CONTACTS LIST / SEARCH
# ------------------------------------------------------------
@contacts_bp.route("/")
def contacts_list():
    search = request.args.get("search", "").strip()

    with get_conn() as conn:
        c = conn.cursor()

        if search:
            rows = c.execute(
                """
                SELECT id, first_name, last_name, email, phone, company, position
                FROM contacts
                WHERE first_name LIKE ? OR last_name LIKE ? OR company LIKE ?
                ORDER BY id DESC
                """,
                (f"%{search}%", f"%{search}%", f"%{search}%")
            ).fetchall()
        else:
            rows = c.execute(
                """
                SELECT id, first_name, last_name, email, phone, company, position
                FROM contacts
                ORDER BY id DESC
                """
            ).fetchall()

    contacts = [
        {
            "id": r["id"],
            "first": r["first_name"],
            "last": r["last_name"],
            "email": r["email"],
            "phone": r["phone"],
            "company": r["company"],
            "position": r["position"],
        }
        for r in rows
    ]

    return render_template("contacts/list.html", contacts=contacts, search=search)


# ------------------------------------------------------------
# ADD CONTACT
# ------------------------------------------------------------
@contacts_bp.route("/add", methods=["GET", "POST"])
def contacts_add():
    if request.method == "POST":
        first = request.form["first_name"]
        last = request.form["last_name"]
        email = request.form.get("email", "")
        phone = request.form.get("phone", "")
        company = request.form.get("company", "")
        position = request.form.get("position", "")
        address = request.form.get("address", "")
        notes = request.form.get("notes", "")

        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO contacts(first_name, last_name, email, phone, company, position, address, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (first, last, email, phone, company, position, address, notes)
            )
            conn.commit()

        return redirect(url_for("contacts.contacts_list"))

    return render_template("contacts/form.html")


# ------------------------------------------------------------
# DELETE CONTACT
# ------------------------------------------------------------
@contacts_bp.route("/delete/<int:id>", methods=["POST"])
def contacts_delete(id):
    with get_conn() as conn:
        conn.execute("DELETE FROM contacts WHERE id=?", (id,))
        conn.commit()

    return redirect(url_for("contacts.contacts_list"))
