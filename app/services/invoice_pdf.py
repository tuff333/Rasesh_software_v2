import os
from flask import render_template, current_app
from weasyprint import HTML, CSS


def generate_invoice_pdf(invoice, vendor, items):
    """
    Generate a professional invoice/estimate/quote PDF.
    Returns: (filename, full_path)
    """

    html = render_template(
        "invoice/pdf_template.html",
        invoice=invoice,
        vendor=vendor,
        items=items
    )

    prefix_map = {
        "Invoice": "INVOICE",
        "Estimate": "ESTIMATE",
        "Quote": "QUOTE"
    }
    prefix = prefix_map.get(invoice.get("invoice_type"), "INVOICE")

    filename = f"{prefix}_{invoice['num']}.pdf"

    output_dir = os.path.join(
        current_app.config["OUTPUT_FOLDER"],
        "invoices"
    )
    os.makedirs(output_dir, exist_ok=True)

    path = os.path.join(output_dir, filename)

    css_path = os.path.join(
        current_app.config["BASE_DIR"],
        "static",
        "css",
        "print.css"
    )

    base_dir = current_app.config["BASE_DIR"]

    HTML(string=html, base_url=base_dir).write_pdf(path, stylesheets=[CSS(css_path)])

    return filename, path
