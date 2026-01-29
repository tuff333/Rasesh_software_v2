from flask import Blueprint, render_template, request, redirect, url_for, send_file, current_app, flash
import sqlite3
import os

invoice_routes_bp = Blueprint("invoice_routes", __name__, url_prefix="/invoice")


def get_conn():
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ------------------------------------------------------------
# LIST INVOICES (Module 8: Filters)
# ------------------------------------------------------------
@invoice_routes_bp.route("/list")
def invoice_list():
    vendor_filter = request.args.get("vendor", "")
    search = request.args.get("search", "")
    date_from = request.args.get("from", "")
    date_to = request.args.get("to", "")
    invoice_type = request.args.get("type", "")

    query = """
        SELECT id, num, date, vendor_id, invoice_type, total, pdf
        FROM invoices
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND num LIKE ?"
        params.append(f"%{search}%")

    if vendor_filter:
        query += " AND vendor_id = ?"
        params.append(vendor_filter)

    if invoice_type:
        query += " AND invoice_type = ?"
        params.append(invoice_type)

    if date_from:
        query += " AND date >= ?"
        params.append(date_from)

    if date_to:
        query += " AND date <= ?"
        params.append(date_to)

    query += " ORDER BY id DESC"

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()

        vendors = {
            r["id"]: r["name"]
            for r in conn.execute("SELECT id, name FROM vendors")
        }

    invoices = []
    for r in rows:
        invoices.append({
            "id": r["id"],
            "num": r["num"],
            "date": r["date"],
            "vendor": vendors.get(r["vendor_id"], "Unknown"),
            "invoice_type": r["invoice_type"],
            "total": r["total"],
            "pdf": r["pdf"]
        })

    return render_template(
        "invoice/list.html",
        invoices=invoices,
        vendors=vendors,
        vendor_filter=vendor_filter,
        search=search,
        date_from=date_from,
        date_to=date_to,
        invoice_type=invoice_type
    )


# ------------------------------------------------------------
# VIEW INVOICE DETAILS
# ------------------------------------------------------------
@invoice_routes_bp.route("/view/<int:invoice_id>")
def invoice_view(invoice_id):
    with get_conn() as conn:
        invoice = conn.execute(
            "SELECT * FROM invoices WHERE id=?",
            (invoice_id,)
        ).fetchone()

        if not invoice:
            return "Invoice not found", 404

        vendor = conn.execute(
            "SELECT * FROM vendors WHERE id=?",
            (invoice["vendor_id"],)
        ).fetchone()

        items = conn.execute(
            """
            SELECT lot_number, item, qty, units, unit_price, line_total
            FROM invoice_items
            WHERE invoice_id=?
            """,
            (invoice_id,)
        ).fetchall()

    return render_template(
        "invoice/view.html",
        invoice=invoice,
        vendor=vendor,
        items=items
    )


# ------------------------------------------------------------
# DOWNLOAD PDF
# ------------------------------------------------------------
@invoice_routes_bp.route("/download/<filename>")
def invoice_download(filename):
    path = os.path.join(
        current_app.config["OUTPUT_FOLDER"],
        "invoices",
        filename
    )
    return send_file(path, as_attachment=True)


# ------------------------------------------------------------
# DELETE INVOICE
# ------------------------------------------------------------
@invoice_routes_bp.route("/delete/<int:invoice_id>", methods=["POST"])
def invoice_delete(invoice_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT pdf FROM invoices WHERE id=?",
            (invoice_id,)
        ).fetchone()

        if row and row["pdf"]:
            pdf_path = os.path.join(
                current_app.config["OUTPUT_FOLDER"],
                "invoices",
                row["pdf"]
            )
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

        conn.execute("DELETE FROM invoice_items WHERE invoice_id=?", (invoice_id,))
        conn.execute("DELETE FROM invoices WHERE id=?", (invoice_id,))
        conn.commit()

    flash("Invoice deleted successfully.", "success")
    return redirect(url_for("invoice_routes.invoice_list"))


# ------------------------------------------------------------
# DUPLICATE INVOICE (Module 9)
# ------------------------------------------------------------
@invoice_routes_bp.route("/duplicate/<int:invoice_id>")
def invoice_duplicate(invoice_id):
    with get_conn() as conn:
        invoice = conn.execute(
            "SELECT * FROM invoices WHERE id=?",
            (invoice_id,)
        ).fetchone()

        if not invoice:
            flash("Invoice not found.", "danger")
            return redirect(url_for("invoice_routes.invoice_list"))

        items = conn.execute(
            """
            SELECT lot_number, item, qty, units, unit_price
            FROM invoice_items
            WHERE invoice_id=?
            """,
            (invoice_id,)
        ).fetchall()

        vendors = conn.execute("SELECT id, name FROM vendors").fetchall()
        gst_numbers = conn.execute("SELECT gst_number FROM gst").fetchall()
        signatures = conn.execute("SELECT id, name, position FROM signatures").fetchall()
        items_master = conn.execute("SELECT name, default_units, default_price FROM items").fetchall()

    return render_template(
        "invoice/form.html",
        vendors=vendors,
        gst_numbers=gst_numbers,
        signatures=signatures,
        items=items_master,
        duplicate_invoice=invoice,
        duplicate_items=items
    )


# ------------------------------------------------------------
# EDIT INVOICE (GET + POST)
# ------------------------------------------------------------
@invoice_routes_bp.route("/edit/<int:invoice_id>", methods=["GET", "POST"])
def invoice_edit(invoice_id):

    # --------------------------
    # POST — SAVE CHANGES
    # --------------------------
    if request.method == "POST":
        invoice_type = request.form.get("invoice_type")
        invoice_number = request.form.get("invoice_number")
        invoice_date = request.form.get("invoice_date")
        vendor_id = request.form.get("vendor_id")
        gst_number = request.form.get("gst_number")
        ship_method = request.form.get("ship_method")
        ship_terms = request.form.get("ship_terms")
        delivery_date = request.form.get("delivery_date")
        comments = request.form.get("comments")
        terms_conditions = request.form.get("terms_conditions")
        sig_id = request.form.get("sig_id")
        template = request.form.get("template")

        # Line items
        lot_numbers = request.form.getlist("lot_number[]")
        items = request.form.getlist("item[]")
        qtys = request.form.getlist("qty[]")
        units = request.form.getlist("units[]")
        prices = request.form.getlist("unit_price[]")

        # Totals
        subtotal = float(request.form.get("subtotal") or 0)
        tax_rate = float(request.form.get("tax_rate") or 0)
        ship_cost = float(request.form.get("ship_cost") or 0)
        total = float(request.form.get("total") or 0)

        with get_conn() as conn:
            cur = conn.cursor()

            # Update invoice header
            cur.execute("""
                UPDATE invoices
                SET invoice_type=?, num=?, date=?, vendor_id=?, gst_number=?,
                    ship_method=?, ship_terms=?, delivery_date=?, comments=?,
                    terms_conditions=?, sig_id=?, template=?, subtotal=?,
                    tax_rate=?, ship_cost=?, total=?
                WHERE id=?
            """, (
                invoice_type, invoice_number, invoice_date, vendor_id, gst_number,
                ship_method, ship_terms, delivery_date, comments,
                terms_conditions, sig_id, template, subtotal,
                tax_rate, ship_cost, total, invoice_id
            ))

            # Delete old items
            cur.execute("DELETE FROM invoice_items WHERE invoice_id=?", (invoice_id,))

            # Insert updated items
            for i in range(len(items)):
                if not items[i]:
                    continue

                cur.execute("""
                    INSERT INTO invoice_items(
                        invoice_id, lot_number, item, qty, units, unit_price, line_total
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    invoice_id,
                    lot_numbers[i],
                    items[i],
                    float(qtys[i] or 0),
                    units[i],
                    float(prices[i] or 0),
                    float(qtys[i] or 0) * float(prices[i] or 0)
                ))

            conn.commit()

        flash("Invoice updated successfully.", "success")
        return redirect(url_for("invoice_routes.invoice_list"))

    # --------------------------
    # GET — LOAD EDIT FORM
    # --------------------------
    with get_conn() as conn:
        invoice = conn.execute(
            "SELECT * FROM invoices WHERE id=?",
            (invoice_id,)
        ).fetchone()

        if not invoice:
            flash("Invoice not found.", "danger")
            return redirect(url_for("invoice_routes.invoice_list"))

        items = conn.execute("""
            SELECT id, lot_number, item, qty, units, unit_price
            FROM invoice_items
            WHERE invoice_id=?
        """, (invoice_id,)).fetchall()

        vendors = conn.execute("SELECT id, name FROM vendors").fetchall()
        gst_numbers = conn.execute("SELECT gst_number FROM gst").fetchall()
        signatures = conn.execute("SELECT id, name, position FROM signatures").fetchall()
        items_master = conn.execute("SELECT name, default_units, default_price FROM items").fetchall()

    return render_template(
        "invoice/form_edit.html",
        invoice=invoice,
        invoice_items=items,
        vendors=vendors,
        gst_numbers=gst_numbers,
        signatures=signatures,
        items=items_master
    )
