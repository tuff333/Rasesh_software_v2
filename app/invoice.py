from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3
from app.database import DB_PATH
from app.services.invoice_numbers import next_invoice_number
from app.services.invoice_pdf import generate_invoice_pdf

invoice_bp = Blueprint("invoice", __name__, url_prefix="/invoice")

@invoice_bp.route("/create", methods=["GET", "POST"])
def invoice_create():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    vendors = conn.execute("SELECT id, name FROM vendors ORDER BY name").fetchall()
    gst_numbers = conn.execute("SELECT gst FROM gst_numbers ORDER BY gst").fetchall()

    if request.method == "POST":
        # Header fields
        vendor_id = request.form.get("vendor_id")
        date = request.form.get("invoice_date", "")

        subtotal = float(request.form.get("subtotal", 0))
        tax = float(request.form.get("tax", 0))
        total = float(request.form.get("total", 0))

        # Generate invoice number
        num = next_invoice_number()

        # Insert invoice header
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO invoices(num, vendor_id, date, subtotal, tax, total)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (num, vendor_id, date, subtotal, tax, total)
        )
        invoice_id = cur.lastrowid

        # Parse line items
        lots = request.form.getlist("lot_number[]")
        items = request.form.getlist("item[]")
        qtys = request.form.getlist("qty[]")
        units = request.form.getlist("units[]")
        prices = request.form.getlist("unit_price[]")

        # Insert line items
        for i in range(len(items)):
            lot = lots[i] if i < len(lots) else ""
            item = items[i]
            qty = float(qtys[i] or 0)
            unit_price = float(prices[i] or 0)
            line_total = qty * unit_price

            cur.execute(
                """
                INSERT INTO invoice_items(invoice_id, lot_number, item, qty, units, unit_price, line_total)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (invoice_id, lot, item, qty, units[i], unit_price, line_total)
            )

        conn.commit()

        # Load vendor for PDF
        vendor = conn.execute(
            "SELECT name, gst_number, address, phone, email FROM vendors WHERE id=?",
            (vendor_id,)
        ).fetchone()

        invoice_obj = {
            "num": num,
            "date": date,
            "subtotal": subtotal,
            "tax": tax,
            "total": total
        }

        vendor_obj = {
            "name": vendor["name"],
            "gst_number": vendor["gst_number"],
            "address": vendor["address"],
            "phone": vendor["phone"],
            "email": vendor["email"]
        }

        # Load items for PDF
        items_for_pdf = conn.execute(
            "SELECT lot_number, item, qty, units, unit_price, line_total FROM invoice_items WHERE invoice_id=?",
            (invoice_id,)
        ).fetchall()

        # Generate PDF
        pdf_name, pdf_path = generate_invoice_pdf(invoice_obj, vendor_obj, items_for_pdf)

        # Save PDF path
        conn.execute(
            "UPDATE invoices SET pdf_path=? WHERE id=?",
            (pdf_name, invoice_id)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("invoice.invoice_list"))

    conn.close()
    return render_template("invoice/form.html", vendors=vendors, gst_numbers=gst_numbers)
