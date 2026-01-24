import fitz
import os
from app.services.settings import get_output_path

def apply_redactions(pdf_path, changes):
    """
    Apply redactions to a PDF and save the result
    using the dynamic output path system.
    Returns: (output_filename, output_path)
    """
    doc = fitz.open(pdf_path)

    # Apply all redactions
    for ch in changes:
        page = doc[ch["page"]]

        if ch["type"] == "area":
            rect = fitz.Rect(
                ch["x"] * page.rect.width,
                ch["y"] * page.rect.height,
                (ch["x"] + ch["width"]) * page.rect.width,
                (ch["y"] + ch["height"]) * page.rect.height
            )
            page.add_redact_annot(rect, fill=(0, 0, 0))

        elif ch["type"] == "text":
            for inst in page.search_for(ch["text"]):
                page.add_redact_annot(inst, fill=(0, 0, 0))

        page.apply_redactions()

    # -----------------------------
    # Output naming: aBcD_Redacted.pdf
    # -----------------------------
    original_name = os.path.basename(pdf_path)
    base, ext = os.path.splitext(original_name)
    output_filename = f"{base}_Redacted{ext}"

    # -----------------------------
    # Dynamic output folder
    # -----------------------------
    output_dir = get_output_path("redaction")
    output_path = os.path.join(output_dir, output_filename)

    # Save final PDF
    doc.save(output_path)
    doc.close()

    return output_filename, output_path
