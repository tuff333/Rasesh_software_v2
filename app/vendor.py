from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3
from .database import DB_PATH

vendor_bp = Blueprint("vendor", __name__, url_prefix="/vendor")

@vendor_bp.route("/")
def vendor_list():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id, name, gst_number, address, phone, email FROM vendors").fetchall()
    conn.close()
    return render_template("vendor/list.html", vendors=rows)

@vendor_bp.route("/add", methods=["GET", "POST"])
def vendor_add():
    if request.method == "POST":
        name = request.form["name"]
        gst = request.form.get("gst_number", "")
        address = request.form.get("address", "")
        phone = request.form.get("phone", "")
        email = request.form.get("email", "")

        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO vendors(name, gst_number, address, phone, email) VALUES(?,?,?,?,?)",
            (name, gst, address, phone, email)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("vendor.vendor_list"))

    return render_template("vendor/form.html")

@vendor_bp.route("/info/<int:id>")
def vendor_info(id):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id, name, gst_number, address, phone, email FROM vendors WHERE id=?",
        (id,)
    ).fetchone()
    conn.close()

    if not row:
        return {"success": False}

    return {
        "success": True,
        "id": row[0],
        "name": row[1],
        "gst": row[2],
        "address": row[3],
        "phone": row[4],
        "email": row[5]
    }
