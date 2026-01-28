from flask import Blueprint, render_template, request, redirect, url_for, current_app
import sqlite3

vendor_bp = Blueprint("vendor", __name__, url_prefix="/vendor")


def get_conn():
    """Return a SQLite connection using the app's configured DB path."""
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ------------------------------------------------------------
# VENDOR LIST
# ------------------------------------------------------------
@vendor_bp.route("/")
def vendor_list():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, gst_number, address, phone, email FROM vendors ORDER BY name"
        ).fetchall()

    return render_template("vendor/list.html", vendors=rows)


# ------------------------------------------------------------
# ADD VENDOR
# ------------------------------------------------------------
@vendor_bp.route("/add", methods=["GET", "POST"])
def vendor_add():
    if request.method == "POST":
        name = request.form["name"]
        gst = request.form.get("gst_number", "")
        address = request.form.get("address", "")
        phone = request.form.get("phone", "")
        email = request.form.get("email", "")

        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO vendors(name, gst_number, address, phone, email)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, gst, address, phone, email)
            )
            conn.commit()

        return redirect(url_for("vendor.vendor_list"))

    return render_template("vendor/form.html")


# ------------------------------------------------------------
# VENDOR INFO (AJAX)
# ------------------------------------------------------------
@vendor_bp.route("/info/<int:id>")
def vendor_info(id):
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, name, gst_number, address, phone, email
            FROM vendors
            WHERE id=?
            """,
            (id,)
        ).fetchone()

    if not row:
        return {"success": False}

    return {
        "success": True,
        "id": row["id"],
        "name": row["name"],
        "gst": row["gst_number"],
        "address": row["address"],
        "phone": row["phone"],
        "email": row["email"]
    }

# ------------------------------------------------------------
# ADD VENDOR (AJAX)
# ------------------------------------------------------------
@vendor_bp.route("/add-ajax", methods=["POST"])
def vendor_add_ajax():
    name = request.form.get("name", "").strip()
    if not name:
        return {"success": False, "error": "Missing vendor name"}

    gst = request.form.get("gst_number", "")
    address = request.form.get("address", "")
    phone = request.form.get("phone", "")
    email = request.form.get("email", "")

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO vendors(name, gst_number, address, phone, email)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, gst, address, phone, email)
        )
        conn.commit()
        new_id = cur.lastrowid

    return {
        "success": True,
        "id": new_id,
        "name": name
    }
