from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3
from .database import DB_PATH

contacts_bp = Blueprint("contacts", __name__, url_prefix="/contacts")

@contacts_bp.route("/")
def contacts_list():
    search = request.args.get("search", "").strip()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if search:
        rows = c.execute('''
            SELECT id, first_name, last_name, email, phone, company, position
            FROM contacts
            WHERE first_name LIKE ? OR last_name LIKE ? OR company LIKE ?
            ORDER BY id DESC
        ''', (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
    else:
        rows = c.execute('''
            SELECT id, first_name, last_name, email, phone, company, position
            FROM contacts
            ORDER BY id DESC
        ''').fetchall()

    conn.close()

    contacts = []
    for r in rows:
        contacts.append({
            "id": r[0],
            "first": r[1],
            "last": r[2],
            "email": r[3],
            "phone": r[4],
            "company": r[5],
            "position": r[6]
        })

    return render_template("contacts/list.html", contacts=contacts, search=search)

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

        conn = sqlite3.connect(DB_PATH)
        conn.execute('''
            INSERT INTO contacts(first_name, last_name, email, phone, company, position, address, notes)
            VALUES(?,?,?,?,?,?,?,?)
        ''', (first, last, email, phone, company, position, address, notes))
        conn.commit()
        conn.close()

        return redirect(url_for("contacts.contacts_list"))

    return render_template("contacts/form.html")

@contacts_bp.route("/delete/<int:id>", methods=["POST"])
def contacts_delete(id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM contacts WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("contacts.contacts_list"))
