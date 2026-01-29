from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify
import sqlite3

invoice_items_bp = Blueprint("invoice_items", __name__, url_prefix="/invoice/items")


def get_conn():
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ------------------------------------------------------------
# LIST ITEMS
# ------------------------------------------------------------
@invoice_items_bp.route("/")
def items_list():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, default_units, default_price FROM items ORDER BY name"
        ).fetchall()

    return render_template("invoice/items_list.html", items=rows)


# ------------------------------------------------------------
# ADD ITEM (GET + POST)
# ------------------------------------------------------------
@invoice_items_bp.route("/add", methods=["GET", "POST"])
def items_add():
    if request.method == "POST":
        name = request.form["name"].strip()
        units = request.form.get("default_units", "")
        price = float(request.form.get("default_price", 0) or 0)

        if name:
            with get_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO items(name, default_units, default_price)
                    VALUES (?, ?, ?)
                    """,
                    (name, units, price)
                )
                conn.commit()

        return redirect(url_for("invoice_items.items_list"))

    return render_template("invoice/items_form.html", item=None)


# ------------------------------------------------------------
# EDIT ITEM
# ------------------------------------------------------------
@invoice_items_bp.route("/edit/<int:item_id>", methods=["GET", "POST"])
def items_edit(item_id):
    with get_conn() as conn:
        item = conn.execute(
            "SELECT id, name, default_units, default_price FROM items WHERE id=?",
            (item_id,)
        ).fetchone()

    if not item:
        return redirect(url_for("invoice_items.items_list"))

    if request.method == "POST":
        name = request.form["name"].strip()
        units = request.form.get("default_units", "")
        price = float(request.form.get("default_price", 0) or 0)

        with get_conn() as conn:
            conn.execute(
                """
                UPDATE items
                SET name=?, default_units=?, default_price=?
                WHERE id=?
                """,
                (name, units, price, item_id)
            )
            conn.commit()

        return redirect(url_for("invoice_items.items_list"))

    return render_template("invoice/items_form.html", item=item)


# ------------------------------------------------------------
# DELETE ITEM (with safety check)
# ------------------------------------------------------------
@invoice_items_bp.route("/delete/<int:item_id>")
def items_delete(item_id):
    with get_conn() as conn:
        # Check if item is used in any invoice
        usage = conn.execute(
            "SELECT COUNT(*) AS cnt FROM invoice_items WHERE item = (SELECT name FROM items WHERE id=?)",
            (item_id,)
        ).fetchone()

        if usage and usage["cnt"] > 0:
            # Store message in session flash
            from flask import flash
            flash("Cannot delete this item because it is used in one or more invoices.", "danger")
            return redirect(url_for("invoice_items.items_list"))

        # Safe to delete
        conn.execute("DELETE FROM items WHERE id=?", (item_id,))
        conn.commit()

    return redirect(url_for("invoice_items.items_list"))

# ------------------------------------------------------------
# JSON API (unchanged)
# ------------------------------------------------------------
@invoice_items_bp.route("/add_json", methods=["POST"])
def items_add_api():
    if not request.is_json:
        return jsonify({"success": False, "error": "JSON required"}), 400

    data = request.get_json()
    name = data.get("name", "").strip()
    units = data.get("default_units", "")
    price = float(data.get("default_price", 0))

    if name:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO items(name, default_units, default_price) VALUES (?, ?, ?)",
                (name, units, price)
            )
            conn.commit()

    return {"success": True}
