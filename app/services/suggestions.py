import fitz

# TEMP SAFE VERSION – OCR + AI suggestions disabled
# This avoids importing pytesseract / pandas / numpy and crashing the app.

def extract_suggestions(pdf_path):
    """
    Safe stub: return an empty list of suggestions.
    The frontend will simply show no AI suggestion buttons.
    """
    return []
