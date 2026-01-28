import os
import fitz
from flask import current_app


def apply_redactions(pdf_path, changes):
    """
    Apply redactions to a PDF and save the result.
    Returns: (output_filename, output_path)
    """

    # Ensure PDF exists
    if not os.path.exists(pdf_path):
        return None, None

    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return None, None

    # Apply all redactions
    for ch in changes:
        page_index = ch.get("page", 0)

        # Validate page index
        if page_index < 0 or page_index >= doc.page_count:
            continue

        page = doc[page_index]

        if ch["type"] == "area":
            rect = fitz.Rect(
                ch["x"] * page.rect.width,
                ch["y"] * page.rect.height,
                (ch["x"] + ch["width"]) * page.rect.width,
                (ch["y"] + ch["height"]) * page.rect.height
            )
            page.add_redact_annot(rect, fill=(0, 0, 0))

        elif ch["type"] == "text":
            text = ch.get("text", "")
            if text:
                for inst in page.search_for(text):
                    page.add_redact_annot(inst, fill=(0, 0, 0))

        page.apply_redactions()

    # Output naming
    original_name = os.path.basename(pdf_path)
    base, ext = os.path.splitext(original_name)
    output_filename = f"{base}_Redacted{ext}"

    # Output folder: BASE/output/redactions
    output_dir = os.path.join(
        current_app.config["OUTPUT_FOLDER"],
        "redactions"
    )
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, output_filename)

    # Save final PDF
    try:
        doc.save(output_path)
    except Exception:
        doc.close()
        return None, None

    doc.close()
    return output_filename, output_path
