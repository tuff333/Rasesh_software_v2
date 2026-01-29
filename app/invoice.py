from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify
import sqlite3
from datetime import date
from app.services.invoice_pdf import generate_invoice_pdf
from app.services.settings import load_settings
from app.services.emailer import send_invoice_email  # will implement separately

invoice_bp = Blueprint("invoice", __name__, url_prefix="/invoice")


def get_conn():
    """Return a SQLite connection using the app's configured DB path."""
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------
# Invoice number sequence helpers (Prefix + Number)
# -------------------------
DEFAULT_INVOICE_PREFIX = "MWR"


def get_next_invoice_number_preview(conn, prefix=DEFAULT_INVOICE_PREFIX):
    row = conn.execute(
        "SELECT last_number FROM invoice_sequences WHERE prefix=?",
        (prefix,)
    ).fetchone()
    last = row["last_number"] if row else 0
    return last + 1


def consume_next_invoice_number(conn, prefix=DEFAULT_INVOICE_PREFIX):
    row = conn.execute(
        "SELECT last_number FROM invoice_sequences WHERE prefix=?",
        (prefix,)
    ).fetchone()

    if row:
        next_num = row["last_number"] + 1
        conn.execute(
            "UPDATE invoice_sequences SET last_number=? WHERE prefix=?",
            (next_num, prefix)
        )
    else:
        next_num = 1
        conn.execute(
            "INSERT INTO invoice_sequences(prefix, last_number) VALUES(?, ?)",
            (prefix, next_num)
        )

    return next_num


# -------------------------
# PREVIEW
# -------------------------
@invoice_bp.route("/preview", methods=["POST"])
def invoice_preview():
    """
    Render a live HTML preview of the invoice before generating PDF.
    """
    with get_conn() as conn:
        # Vendor
        vendor_id = request.form.get("vendor_id")
        vendor = conn.execute(
            "SELECT name, gst_number, address, phone, email FROM vendors WHERE id=?",
            (vendor_id,)
        ).fetchone()
        vendor_obj = dict(vendor) if vendor else {}

        # Signature
        sig_id = request.form.get("sig_id")
        signature = None
        if sig_id:
            signature = conn.execute(
                "SELECT name, position, filename FROM signatures WHERE id=?",
                (sig_id,)
            ).fetchone()

        # Build signature info
        signature_name = None
        signature_image_path = None
        if signature:
            if signature["position"]:
                signature_name = f"{signature['name']} ({signature['position']})"
            else:
                signature_name = signature["name"]

            signature_image_path = f"static/signatures/{signature['filename']}"

        # Delivery date polish
        delivery_date = request.form.get("delivery_date")
        if delivery_date == "TBD":
            delivery_date = None

        # Template
        template = request.form.get("template") or "classic"

        # Build invoice object
        invoice_obj = {
            "num": request.form.get("invoice_number") or "PREVIEW",
            "date": request.form.get("invoice_date"),
            "invoice_type": request.form.get("invoice_type"),
            "comments": request.form.get("comments"),
            "terms_conditions": request.form.get("terms_conditions"),
            "ship_cost": float(request.form.get("ship_cost") or 0),
            "tax_rate": float(request.form.get("tax_rate") or 0),
            "tax": float(request.form.get("tax") or 0),
            "subtotal": float(request.form.get("subtotal") or 0),
            "total": float(request.form.get("total") or 0),
            "delivery_date": delivery_date,
            "signature_name": signature_name,
            "signature_image_path": signature_image_path,
            "gst_number": request.form.get("gst_number") or "",
            "template": template,
        }

        # Build line items
        items = []
        lots = request.form.getlist("lot_number[]")
        names = request.form.getlist("item[]")
        qtys = request.form.getlist("qty[]")
        units = request.form.getlist("units[]")
        prices = request.form.getlist("unit_price[]")

        for i in range(len(names)):
            if not names[i].strip():
                continue

            qty = float(qtys[i] or 0)
            price = float(prices[i] or 0)
            line_total = qty * price

            items.append({
                "lot_number": lots[i],
                "item": names[i],
                "qty": qty,
                "units": units[i],
                "unit_price": price,
                "price": price,
                "line_total": line_total,
                "total": line_total,
            })

    return render_template(
        "invoice/preview.html",
        invoice=invoice_obj,
        vendor=vendor_obj,
        items=items
    )


# -------------------------
# CREATE
# -------------------------
@invoice_bp.route("/create", methods=["GET", "POST"])
def invoice_create():
    settings = load_settings()
    default_template = settings.get("default_template", "classic")
    settings_default_signature_id = settings.get("default_signature_id") or ""
    settings_default_gst = settings.get("default_gst") or ""

    with get_conn() as conn:
        # Vendors
        vendors = conn.execute(
            "SELECT id, name FROM vendors ORDER BY name"
        ).fetchall()

        # GST numbers
        gst_numbers = conn.execute(
            "SELECT id, gst_number, is_default FROM gst ORDER BY gst_number"
        ).fetchall()

        # DB default GST (is_default=1)
        default_gst_row = conn.execute(
            "SELECT gst_number FROM gst WHERE is_default=1 LIMIT 1"
        ).fetchone()
        db_default_gst = default_gst_row["gst_number"] if default_gst_row else None

        # Effective default GST: settings overrides DB
        effective_default_gst = settings_default_gst or db_default_gst

        # Items
        items = conn.execute(
            "SELECT name, default_units, default_price FROM items ORDER BY name"
        ).fetchall()

        # Signatures
        signatures = conn.execute(
            "SELECT id, name, position, filename, is_default FROM signatures ORDER BY id"
        ).fetchall()

        # DB default signature
        db_default_signature_id = None
        for s in signatures:
            if s["is_default"]:
                db_default_signature_id = s["id"]
                break

        # Effective default signature: settings overrides DB
        effective_default_signature_id = settings_default_signature_id or db_default_signature_id

        if request.method == "POST":
            vendor_id = request.form.get("vendor_id")
            invoice_type = request.form.get("invoice_type", "Invoice")
            date_str = request.form.get("invoice_date", "")

            comments = request.form.get("comments", "")
            terms = request.form.get("terms_conditions", "")

            ship_cost = float(request.form.get("ship_cost", 0) or 0)
            tax_rate = float(request.form.get("tax_rate", 0) or 0)
            tax = float(request.form.get("tax", 0) or 0)
            subtotal = float(request.form.get("subtotal", 0) or 0)
            total = float(request.form.get("total", 0) or 0)

            # Delivery date
            delivery_date = request.form.get("delivery_date", "")
            if delivery_date == "TBD":
                delivery_date = None

            # Template
            template = request.form.get("template") or default_template

            # GST number
            gst_number = request.form.get("gst_number") or effective_default_gst or ""

            # Signature selection
            sig_id = request.form.get("sig_id") or None
            sig_row = None
            if sig_id:
                sig_row = conn.execute(
                    "SELECT name, position, filename FROM signatures WHERE id=?",
                    (sig_id,),
                ).fetchone()
            elif effective_default_signature_id:
                sig_row = conn.execute(
                    "SELECT name, position, filename FROM signatures WHERE id=?",
                    (effective_default_signature_id,),
                ).fetchone()

            # Editable invoice number
            user_num = (request.form.get("invoice_number") or "").strip()
            if user_num:
                num = user_num
            else:
                next_seq = consume_next_invoice_number(conn, DEFAULT_INVOICE_PREFIX)
                num = f"{DEFAULT_INVOICE_PREFIX} - {next_seq}"

            # INSERT INVOICE HEADER
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO invoices(
                    num, date, vendor_id, invoice_type,
                    comments, terms_conditions, sig_id,
                    ship_cost, tax_rate, tax, subtotal, total,
                    delivery_date, gst_number, template
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    num, date_str, vendor_id, invoice_type,
                    comments, terms, sig_id,
                    ship_cost, tax_rate, tax, subtotal, total,
                    delivery_date, gst_number, template
                )
            )
            invoice_id = cur.lastrowid

            # LINE ITEMS
            lots = request.form.getlist("lot_number[]")
            items_form = request.form.getlist("item[]")
            qtys = request.form.getlist("qty[]")
            units = request.form.getlist("units[]")
            prices = request.form.getlist("unit_price[]")

            for i in range(len(items_form)):
                item_name = items_form[i]
                if not item_name.strip():
                    continue

                lot = lots[i] if i < len(lots) else ""
                qty = float(qtys[i] or 0)
                unit_price = float(prices[i] or 0)
                line_total = qty * unit_price

                cur.execute(
                    """
                    INSERT INTO invoice_items(
                        invoice_id, lot_number, item, qty, units, unit_price, line_total
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (invoice_id, lot, item_name, qty, units[i], unit_price, line_total)
                )

            conn.commit()

            # VENDOR FOR PDF
            vendor = conn.execute(
                "SELECT name, gst_number, address, phone, email FROM vendors WHERE id=?",
                (vendor_id,),
            ).fetchone()
            vendor_obj = dict(vendor) if vendor else {}

            # ITEMS FOR PDF
            items_for_pdf = conn.execute(
                """
                SELECT lot_number, item, qty, units, unit_price, line_total
                FROM invoice_items
                WHERE invoice_id=?
                """,
                (invoice_id,),
            ).fetchall()

            # SIGNATURE INFO FOR PDF
            signature_name = None
            signature_position = None
            signature_image_path = None
            if sig_row:
                signature_name = sig_row["name"]
                if sig_row["position"]:
                    signature_name = f"{sig_row['name']} ({sig_row['position']})"
                signature_position = sig_row["position"]
                signature_image_path = f"static/signatures/{sig_row['filename']}"

            # INVOICE OBJECT
            invoice_obj = {
                "num": num,
                "date": date_str,
                "invoice_type": invoice_type,
                "comments": comments,
                "terms_conditions": terms,
                "ship_cost": ship_cost,
                "tax_rate": tax_rate,
                "tax": tax,
                "subtotal": subtotal,
                "total": total,
                "delivery_date": delivery_date,
                "signature_name": signature_name,
                "signature_position": signature_position,
                "signature_image_path": signature_image_path,
                "gst_number": gst_number,
                "template": template,
            }

            # GENERATE PDF (template-aware via invoice_obj)
            pdf_name, pdf_path = generate_invoice_pdf(
                invoice_obj, vendor_obj, items_for_pdf
            )

            conn.execute(
                "UPDATE invoices SET pdf=? WHERE id=?",
                (pdf_name, invoice_id)
            )
            conn.commit()

            return redirect(url_for("invoice_routes.invoice_list"))

    # GET: defaults
    today_str = date.today().isoformat()
    with get_conn() as conn_preview:
        next_preview = get_next_invoice_number_preview(conn_preview, DEFAULT_INVOICE_PREFIX)
        suggested_invoice_number = f"{DEFAULT_INVOICE_PREFIX} - {next_preview}"

    return render_template(
        "invoice/form.html",
        vendors=vendors,
        gst_numbers=gst_numbers,
        items=items,
        signatures=signatures,
        today=today_str,
        default_gst=effective_default_gst,
        default_signature_id=effective_default_signature_id,
        default_template=default_template,
        suggested_invoice_number=suggested_invoice_number
    )


# -------------------------
# SEND INVOICE BY EMAIL
# -------------------------
@invoice_bp.route("/send/<int:invoice_id>", methods=["POST"])
def invoice_send_email(invoice_id):
    """
    Send an invoice by email with attached PDF.
    Expects JSON: { "to": "...", "subject": "...", "body": "..." }
    """
    data = request.json or {}
    to_email = data.get("to")
    subject = data.get("subject") or "Invoice"
    body = data.get("body") or ""

    if not to_email:
        return jsonify({"success": False, "error": "Missing 'to' email"}), 400

    with get_conn() as conn:
        invoice = conn.execute(
            "SELECT * FROM invoices WHERE id=?",
            (invoice_id,)
        ).fetchone()
        if not invoice:
            return jsonify({"success": False, "error": "Invoice not found"}), 404

        vendor = conn.execute(
            "SELECT name, email FROM vendors WHERE id=?",
            (invoice["vendor_id"],)
        ).fetchone()

        pdf_name = invoice["pdf"]
        if not pdf_name:
            return jsonify({"success": False, "error": "Invoice PDF not generated"}), 400

        pdf_path = current_app.config["OUTPUT_FOLDER"] + "/invoices/" + pdf_name

    ok, err = send_invoice_email(
        to_email,
        subject,
        body,
        pdf_path,
        vendor_name=vendor["name"] if vendor else None
    )

    if not ok:
        return jsonify({"success": False, "error": err or "Failed to send email"}), 500

    return jsonify({"success": True})
