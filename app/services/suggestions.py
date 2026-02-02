"""
suggestions.py – Redactor AI/OCR suggestion engine (spaCy + YOLO)

Uses your trained models to propose redaction regions:
- YOLO: visual bounding boxes (signatures, logos, etc.)
- spaCy: text entities (names, emails, phones, etc.)

Output format matches what the frontend expects:
  {
    "label": "Name",
    "text": "John Doe",
    "page": 0,
    "bbox": [x1, y1, x2, y2],   # for area-based redactions (YOLO)
    "mode": "area" or "text"
  }
"""

import io
import os

import fitz
import numpy as np
from PIL import Image

from app.services.ocr import ocr_page

# These imports assume you installed:
#   pip install spacy ultralytics
try:
    import spacy
    from ultralytics import YOLO
except ImportError:
    spacy = None
    YOLO = None

# -------------------------------------------------------------------
# MODEL PATHS – ADJUST IF YOUR FILE NAMES DIFFER
# -------------------------------------------------------------------

SPACY_MODEL_DIR = r"C:\projects\Rasesh_software\Ai\trained_model\spacy"
YOLO_MODEL_PATH = r"C:\projects\Rasesh_software\Ai\trained_model\yolo\best.pt"

_nlp = None
_yolo_model = None


def _load_models():
    """
    Lazy-load spaCy + YOLO models once per process.
    If anything fails, we fall back to no suggestions.
    """
    global _nlp, _yolo_model

    if spacy is None or YOLO is None:
        return

    if _nlp is None:
        try:
            _nlp = spacy.load(SPACY_MODEL_DIR)
        except Exception:
            _nlp = None

    if _yolo_model is None:
        try:
            _yolo_model = YOLO(YOLO_MODEL_PATH)
        except Exception:
            _yolo_model = None


def _page_image(doc, page_index, dpi=150):
    """
    Render a single PDF page to a PIL image.
    Returns PIL.Image or None.
    """
    try:
        page = doc[page_index]
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        return img
    except Exception:
        return None


def _run_yolo_on_page(img, page_index):
    """
    Run YOLO on a PIL image and return area-based suggestions.
    Each suggestion has a bounding box in pixel coordinates.
    """
    if _yolo_model is None or img is None:
        return []

    suggestions = []

    try:
        arr = np.array(img)
        results = _yolo_model(arr)
    except Exception:
        return []

    if not results:
        return suggestions

    res = results[0]
    if not hasattr(res, "boxes") or res.boxes is None:
        return suggestions

    for box in res.boxes:
        try:
            xyxy = box.xyxy[0].tolist()
            x1, y1, x2, y2 = xyxy
            cls_idx = int(box.cls[0])
            label = _yolo_model.names.get(cls_idx, f"class_{cls_idx}")
        except Exception:
            continue

        suggestions.append(
            {
                "label": label,
                "text": label,
                "page": page_index,
                "bbox": [float(x1), float(y1), float(x2), float(y2)],
                "mode": "area",
            }
        )

    return suggestions


def _run_spacy_on_page(text, page_index):
    """
    Run spaCy NER on text and return text-based suggestions.
    These do NOT have bounding boxes; they rely on text search.
    """
    if _nlp is None or not text:
        return []

    try:
        doc = _nlp(text)
    except Exception:
        return []

    suggestions = []
    for ent in doc.ents:
        suggestions.append(
            {
                "label": ent.label_,
                "text": ent.text,
                "page": page_index,
                "bbox": None,
                "mode": "text",
            }
        )

    return suggestions


def extract_suggestions(pdf_path, use_ocr=False):
    """
    Main entry point used by routes.py.

    - pdf_path: full path to the uploaded PDF
    - use_ocr: if True, also run OCR and feed that text into spaCy

    Returns a flat list of suggestion dicts.
    """
    if not os.path.exists(pdf_path):
        return []

    _load_models()

    # If both models failed to load, just return empty.
    if _nlp is None and _yolo_model is None:
        return []

    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return []

    all_suggestions = []

    try:
        page_count = doc.page_count
        for p in range(page_count):
            # 1) Render page image for YOLO
            img = _page_image(doc, p)

            # 2) Extract text for spaCy
            try:
                page = doc[p]
                text = page.get_text("text") or ""
            except Exception:
                text = ""

            # Optional OCR text
            if use_ocr:
                try:
                    ocr_text = ocr_page(pdf_path, p)
                    if ocr_text:
                        text = text + "\n" + ocr_text
                except Exception:
                    pass

            # YOLO suggestions (area-based)
            all_suggestions.extend(_run_yolo_on_page(img, p))

            # spaCy suggestions (text-based)
            all_suggestions.extend(_run_spacy_on_page(text, p))

    finally:
        doc.close()

    return all_suggestions
