from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3
from .database import DB_PATH

manifest_bp = Blueprint("manifest", __name__, url_prefix="/manifest")

@manifest_bp.route("/")
def manifest_registry():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute('''
        SELECT id, num, date, carrier, ship_from, ship_to, weight, pdf_path
        FROM manifests
        ORDER BY id DESC
    ''').fetchall()
    conn.close()

    manifests = []
    for r in rows:
        manifests.append({
            "id": r[0],
            "num": r[1],
            "date": r[2],
            "carrier": r[3],
            "ship_from": r[4],
            "ship_to": r[5],
            "weight": r[6],
            "pdf": r[7]
        })

    return render_template("manifest/registry.html", manifests=manifests)

@manifest_bp.route("/create", methods=["GET", "POST"])
def manifest_create():
    import datetime as dt
    conn = sqlite3.connect(DB_PATH)
    signatures = []  # placeholder if you add signatures later

    if request.method == "POST":
        manifest_date = request.form["manifest_date"]
        carrier = request.form.get("carrier", "")
        delivery_date = request.form.get("delivery_date", "")
        ship_from = request.form["ship_from"]
        ship_to = request.form["ship_to"]
        contact_name = request.form.get("contact_name", "")
        ship_method = request.form.get("ship_method", "")

        items = request.form.getlist("item")
        lots = request.form.getlist("lot_number")
        weights = request.form.getlist("weight")

        total_weight = sum(float(w or 0) for w in weights)

        cur = conn.cursor()
        cur.execute('''
            INSERT INTO manifests(num, date, carrier, delivery, ship_from, ship_to, contact, weight, pdf_path)
            VALUES(?,?,?,?,?,?,?,?,?)
        ''', (
            "", manifest_date, carrier, delivery_date, ship_from, ship_to,
            contact_name, total_weight, ""
        ))
        mid = cur.lastrowid

        for i in range(len(items)):
            cur.execute('''
                INSERT INTO manifest_items(manifest_id, item, lot, weight)
                VALUES(?,?,?,?)
            ''', (mid, items[i], lots[i], float(weights[i] or 0)))

        conn.commit()
        conn.close()

        return redirect(url_for("manifest.manifest_registry"))

    today = dt.date.today().isoformat()
    conn.close()
    return render_template("manifest/form.html", today=today, signatures=signatures)

@manifest_bp.route("/preview/<int:id>")
def manifest_preview(id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    m = cur.execute('''
        SELECT num, date, carrier, delivery, ship_from, ship_to, contact, weight, pdf_path
        FROM manifests WHERE id=?
    ''', (id,)).fetchone()

    items = cur.execute('''
        SELECT item, lot, weight
        FROM manifest_items
        WHERE manifest_id=?
    ''', (id,)).fetchall()
    conn.close()

    manifest = {
        "num": m[0],
        "date": m[1],
        "carrier": m[2],
        "delivery": m[3],
        "ship_from": m[4],
        "ship_to": m[5],
        "contact": m[6],
        "weight": m[7],
        "pdf": m[8],
        "simg": None,
        "sn": "",
        "sp": ""
    }

    items_obj = []
    for it in items:
        items_obj.append({
            "item": it[0],
            "lot": it[1],
            "weight": it[2]
        })

    return render_template("manifest/preview.html", manifest=manifest, items=items_obj)
