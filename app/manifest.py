import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, current_app

manifest_bp = Blueprint("manifest", __name__, url_prefix="/manifest")


def get_conn():
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ------------------------------------------------------------
# REGISTRY
# ------------------------------------------------------------
@manifest_bp.route("/")
def manifest_registry():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, num, date, carrier, ship_from, ship_to,
                   total_weight AS weight, pdf
            FROM manifests
            ORDER BY id DESC
        """).fetchall()

    manifests = [
        {
            "id": r["id"],
            "num": r["num"],
            "date": r["date"],
            "carrier": r["carrier"],
            "ship_from": r["ship_from"],
            "ship_to": r["ship_to"],
            "weight": r["weight"],
            "pdf": r["pdf"]
        }
        for r in rows
    ]

    return render_template("manifest/registry.html", manifests=manifests)


# ------------------------------------------------------------
# CREATE MANIFEST
# ------------------------------------------------------------
@manifest_bp.route("/create", methods=["GET", "POST"])
def manifest_create():
    import datetime as dt
    signatures = []  # placeholder for future signature support

    if request.method == "POST":
        manifest_date = request.form["manifest_date"]
        carrier = request.form.get("carrier", "")
        delivery_date = request.form.get("delivery_date", "")
        ship_from = request.form["ship_from"]
        ship_to = request.form["ship_to"]
        contact_name = request.form.get("contact_name", "")
        ship_method = request.form.get("ship_method", "")
        sig_id = request.form.get("sig_id") or None

        items = request.form.getlist("item")
        lots = request.form.getlist("lot_number")
        weights = request.form.getlist("weight")

        total_weight = sum(float(w or 0) for w in weights)

        with get_conn() as conn:
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO manifests(
                    num, date, carrier, delivery, ship_from, ship_to,
                    contact_name, ship_method, sig_id, total_weight, pdf
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "",  # num placeholder
                manifest_date,
                carrier,
                delivery_date,
                ship_from,
                ship_to,
                contact_name,
                ship_method,
                sig_id,
                total_weight,
                ""  # pdf placeholder
            ))

            mid = cur.lastrowid

            for i in range(len(items)):
                cur.execute("""
                    INSERT INTO manifest_items(manifest_id, item, lot, weight)
                    VALUES (?, ?, ?, ?)
                """, (
                    mid,
                    items[i],
                    lots[i],
                    float(weights[i] or 0)
                ))

            conn.commit()

        return redirect(url_for("manifest.manifest_registry"))

    today = dt.date.today().isoformat()
    return render_template("manifest/form.html", today=today, signatures=signatures)


# ------------------------------------------------------------
# PREVIEW MANIFEST
# ------------------------------------------------------------
@manifest_bp.route("/preview/<int:id>")
def manifest_preview(id):
    with get_conn() as conn:
        cur = conn.cursor()

        m = cur.execute("""
            SELECT num, date, carrier, delivery, ship_from, ship_to,
                   contact_name, ship_method, sig_id, total_weight, pdf
            FROM manifests
            WHERE id=?
        """, (id,)).fetchone()

        items = cur.execute("""
            SELECT item, lot, weight
            FROM manifest_items
            WHERE manifest_id=?
        """, (id,)).fetchall()

    manifest = {
        "num": m["num"],
        "date": m["date"],
        "carrier": m["carrier"],
        "delivery": m["delivery"],
        "ship_from": m["ship_from"],
        "ship_to": m["ship_to"],
        "contact": m["contact_name"],
        "ship_method": m["ship_method"],
        "sig_id": m["sig_id"],
        "weight": m["total_weight"],
        "pdf": m["pdf"],
        "sig_img": None,  # future support
    }

    items_obj = [
        {
            "item": it["item"],
            "lot": it["lot"],
            "weight": it["weight"]
        }
        for it in items
    ]

    return render_template(
        "manifest/preview.html",
        manifest=manifest,
        items=items_obj,
        total_weight=m["total_weight"]
    )
