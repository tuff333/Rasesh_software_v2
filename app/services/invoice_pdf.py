import os
from weasyprint import HTML
from flask import render_template
from settings import settings  # root-level settings.py

def generate_invoice_pdf(invoice, vendor, items):
    """
    Generate a professional invoice PDF with line items.
    Uses output_invoices from settings.json.
    Returns: (filename, full_path)
    """
    html = render_template(
        "invoice/pdf_template.html",
        invoice=invoice,
        vendor=vendor,
        items=items
    )

    filename = f"INVOICE_{invoice['num']}.pdf"

    # Ensure output folder exists
    output_dir = settings.get("output_invoices", "output/invoices")
    os.makedirs(output_dir, exist_ok=True)

    path = os.path.join(output_dir, filename)
    HTML(string=html).write_pdf(path)

    return filename, path
