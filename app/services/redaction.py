import os
import fitz
from flask import current_app


def apply_redactions(pdf_path, changes):
    """
    Apply redactions to a PDF and save the result.
    'changes' is a list of dicts with normalized coordinates:
      {
        "page": 0,
        "x": 0.1,
        "y": 0.2,
        "width": 0.3,
        "height": 0.1,
        "type": "area" or "text",
        "text": "optional"
      }

    Returns: (output_filename, output_path) or (None, None) on failure.
    """

    if not os.path.exists(pdf_path):
        return None, None

    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return None, None

    # Apply all redactions
    for ch in changes:
        page_index = ch.get("page", 0)

        if page_index < 0 or page_index >= doc.page_count:
            continue

        page = doc[page_index]

        if ch.get("type") == "area":
            x = ch.get("x", 0.0)
            y = ch.get("y", 0.0)
            w = ch.get("width", 0.0)
            h = ch.get("height", 0.0)

            rect = fitz.Rect(
                x * page.rect.width,
                y * page.rect.height,
                (x + w) * page.rect.width,
                (y + h) * page.rect.height,
            )
            page.add_redact_annot(rect, fill=(0, 0, 0))

        elif ch.get("type") == "text":
            text = ch.get("text", "")
            if text:
                for inst in page.search_for(text):
                    page.add_redact_annot(inst, fill=(0, 0, 0))

        # Apply redactions for this page
        page.apply_redactions()

    # Build output name
    original_name = os.path.basename(pdf_path)
    base, ext = os.path.splitext(original_name)
    output_filename = f"{base}_Redacted{ext}"

    output_dir = os.path.join(
        current_app.config["OUTPUT_FOLDER"],
        "redactions",
    )
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, output_filename)

    try:
        doc.save(output_path)
    except Exception:
        doc.close()
        return None, None

    doc.close()
    return output_filename, output_path
