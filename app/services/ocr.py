import io
import os
import fitz
import pytesseract
from PIL import Image
from flask import current_app


def ocr_page(pdf_path, page_num, dpi=300):
    """Extract text from a scanned PDF page using OCR."""

    # Ensure PDF exists
    if not os.path.exists(pdf_path):
        return ""

    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return ""

    # Validate page index
    if page_num < 0 or page_num >= doc.page_count:
        doc.close()
        return ""

    try:
        # Render page as high-resolution image
        pix = doc[page_num].get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
    except Exception:
        doc.close()
        return ""

    doc.close()

    # Convert to PIL image
    try:
        img = Image.open(io.BytesIO(img_bytes))
    except Exception:
        return ""

    # Convert to grayscale (improves OCR accuracy)
    img = img.convert("L")

    # OCR
    try:
        text = pytesseract.image_to_string(img)
    except Exception:
        text = ""

    return text


def ocr_document(pdf_path, dpi=300):
    """Extract OCR text for all pages."""

    # Ensure PDF exists
    if not os.path.exists(pdf_path):
        return []

    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return []

    pages = doc.page_count
    doc.close()

    return [ocr_page(pdf_path, p, dpi=dpi) for p in range(pages)]
