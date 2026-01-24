import pytesseract
import fitz
from PIL import Image
import io

def ocr_page(pdf_path, page_num, dpi=300):
    """Extract text from a scanned PDF page using OCR."""
    doc = fitz.open(pdf_path)
    if page_num < 0 or page_num >= doc.page_count:
        doc.close()
        return ""

    # Render page as high-resolution image
    pix = doc[page_num].get_pixmap(dpi=dpi)
    img_bytes = pix.tobytes("png")
    doc.close()

    # Convert to PIL image
    img = Image.open(io.BytesIO(img_bytes))

    # OCR
    text = pytesseract.image_to_string(img)
    return text


def ocr_document(pdf_path, dpi=300):
    """Extract OCR text for all pages."""
    doc = fitz.open(pdf_path)
    pages = doc.page_count
    doc.close()

    return [ocr_page(pdf_path, p, dpi=dpi) for p in range(pages)]
