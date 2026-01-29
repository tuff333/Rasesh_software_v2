import os
import subprocess
from flask import render_template, current_app


def generate_invoice_pdf(invoice, vendor, items):
    """
    Generate invoice/estimate/quote PDF using wkhtmltopdf (Windows‑safe).
    Returns: (filename, full_path)
    """

    # Render HTML from template
    html = render_template(
        "invoice/pdf_template.html",
        invoice=invoice,
        vendor=vendor,
        items=items
    )

    # Determine prefix based on invoice type
    prefix_map = {
        "Invoice": "INVOICE",
        "Estimate": "ESTIMATE",
        "Quote": "QUOTE"
    }
    prefix = prefix_map.get(invoice.get("invoice_type"), "INVOICE")

    # Output filename
    filename = f"{prefix}_{invoice['num']}.pdf"

    # Output directory
    output_dir = os.path.join(
        current_app.config["OUTPUT_FOLDER"],
        "invoices"
    )
    os.makedirs(output_dir, exist_ok=True)

    pdf_path = os.path.join(output_dir, filename)

    # Temporary HTML file
    temp_html_path = os.path.join(output_dir, f"{filename}.html")
    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Path to wkhtmltopdf
    wkhtml_path = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"

    # CSS file
    css_path = os.path.join(
        current_app.config["BASE_DIR"],
        "static",
        "css",
        "print.css"
    )

    # Build wkhtmltopdf command
    command = [
        wkhtml_path,
        "--enable-local-file-access",
        "--print-media-type",
        temp_html_path,
        pdf_path
    ]

    # Run wkhtmltopdf
    try:
        subprocess.run(command, check=True)
    except Exception as e:
        raise RuntimeError(f"wkhtmltopdf failed: {e}")

    # Cleanup temp HTML
    if os.path.exists(temp_html_path):
        os.remove(temp_html_path)

    return filename, pdf_path
