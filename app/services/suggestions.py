"""
suggestions.py – Redactor AI/OCR suggestion engine (currently disabled)

This module intentionally returns no suggestions to keep the
application lightweight and avoid heavy dependencies such as
pytesseract, numpy, or pandas.

The frontend gracefully handles an empty list and simply shows
no suggestion buttons.
"""

def extract_suggestions(pdf_path):
    """
    Return an empty list of suggestions.
    Future versions may integrate OCR or AI-based text detection.
    """
    return []
