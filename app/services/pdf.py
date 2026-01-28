import os
import fitz
from flask import current_app


def temp_image_path(filename, page_num):
    """
    Return a consistent temp thumbnail path:
    BASE/output/temp/<filename>_page_<n>.png
    """
    temp_dir = os.path.join(
        current_app.config["OUTPUT_FOLDER"],
        "temp"
    )
    os.makedirs(temp_dir, exist_ok=True)

    safe_name = filename.replace("/", "_").replace("\\", "_")
    return os.path.join(temp_dir, f"{safe_name}_page_{page_num}.png")


def render_page(pdf_path, page_num, dpi=150):
    """
    Render a PDF page to a PNG image at the given DPI.
    Returns the output PNG path or None.
    """

    # Ensure PDF exists
    if not os.path.exists(pdf_path):
        return None

    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return None

    # Validate page number
    if page_num < 0 or page_num >= doc.page_count:
        doc.close()
        return None

    # Render page
    pix = doc[page_num].get_pixmap(dpi=dpi)

    # Extract filename only
    fname = os.path.basename(pdf_path)

    # Build output path
    out = temp_image_path(fname, page_num)

    # Save PNG
    pix.save(out)

    doc.close()
    return out
