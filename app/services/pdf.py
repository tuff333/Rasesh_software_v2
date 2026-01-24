import fitz
from app.storage import temp_image_path

def render_page(pdf_path, page_num, dpi=150):
    """Render a PDF page to a PNG image at the given DPI."""
    doc = fitz.open(pdf_path)
    if page_num < 0 or page_num >= doc.page_count:
        doc.close()
        return None

    pix = doc[page_num].get_pixmap(dpi=dpi)

    # Extract filename only
    fname = pdf_path.replace("\\", "/").split("/")[-1]

    out = temp_image_path(fname, page_num)
    pix.save(out)
    doc.close()
    return out
