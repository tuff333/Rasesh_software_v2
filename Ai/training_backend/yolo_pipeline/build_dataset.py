import os
from pathlib import Path
from typing import List, Tuple

import fitz
from PIL import Image
import numpy as np
import cv2

# BASE_DIR = ...\Ai
BASE_DIR = Path(__file__).resolve().parents[2]

ORIGINAL_DIR = BASE_DIR / "training_data" / "original"
REDACTED_DIR = BASE_DIR / "training_data" / "redacted"

OUTPUT_IMAGES = BASE_DIR / "training_data" / "yolo_dataset" / "images"
OUTPUT_LABELS = BASE_DIR / "training_data" / "yolo_dataset" / "labels"

CLASS_ID = 0  # SENSITIVE

def ensure_dirs():
    OUTPUT_IMAGES.mkdir(parents=True, exist_ok=True)
    OUTPUT_LABELS.mkdir(parents=True, exist_ok=True)

def find_matching_redacted(original_name: str) -> str | None:
    base = Path(original_name).stem
    candidates = [
        f"{base}_Redacted.pdf",
        f"{base}_redacted.pdf",
        f"{base} - Redacted.pdf",
    ]
    for c in candidates:
        p = REDACTED_DIR / c
        if p.exists():
            return str(p)
    return None

def pdf_page_to_image(doc: fitz.Document, page_index: int) -> Image.Image:
    page = doc[page_index]
    mat = fitz.Matrix(2, 2)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img

def detect_redaction_boxes(orig_img: Image.Image, red_img: Image.Image):
    orig = np.array(orig_img.convert("L"))
    red = np.array(red_img.convert("L"))

    diff = orig - red
    diff = np.clip(diff, 0, 255).astype("uint8")

    _, thresh = cv2.threshold(diff, 40, 255, cv2.THRESH_BINARY)

    kernel = np.ones((5, 5), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    h, w = thresh.shape
    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw < 10 or bh < 10:
            continue
        boxes.append((x, y, x + bw, y + bh))

    return boxes, (w, h)

def to_yolo_format(boxes, img_size):
    w_img, h_img = img_size
    yolo_lines = []
    for x_min, y_min, x_max, y_max in boxes:
        x_c = (x_min + x_max) / 2.0 / w_img
        y_c = (y_min + y_max) / 2.0 / h_img
        bw = (x_max - x_min) / w_img
        bh = (y_max - y_min) / h_img
        yolo_lines.append(f"{CLASS_ID} {x_c:.6f} {y_c:.6f} {bw:.6f} {bh:.6f}")
    return yolo_lines

def process_pair(original_pdf: str, redacted_pdf: str):
    orig_doc = fitz.open(original_pdf)
    red_doc = fitz.open(redacted_pdf)

    if len(orig_doc) != len(red_doc):
        print(f"[WARN] Page count mismatch: {original_pdf}")
        return

    base_name = Path(original_pdf).stem

    for page_idx in range(len(orig_doc)):
        orig_img = pdf_page_to_image(orig_doc, page_idx)
        red_img = pdf_page_to_image(red_doc, page_idx)

        boxes, (w, h) = detect_redaction_boxes(orig_img, red_img)
        if not boxes:
            continue

        img_out = OUTPUT_IMAGES / f"{base_name}_p{page_idx+1}.jpg"
        lbl_out = OUTPUT_LABELS / f"{base_name}_p{page_idx+1}.txt"

        orig_img.save(img_out, "JPEG")

        yolo_lines = to_yolo_format(boxes, (w, h))
        with open(lbl_out, "w", encoding="utf-8") as f:
            f.write("\n".join(yolo_lines))

    orig_doc.close()
    red_doc.close()

def build_dataset():
    ensure_dirs()
    originals = [f for f in os.listdir(ORIGINAL_DIR) if f.lower().endswith(".pdf")]

    for fname in originals:
        orig_path = ORIGINAL_DIR / fname
        red_path = find_matching_redacted(fname)
        if not red_path:
            print(f"[WARN] No redacted match for: {fname}")
            continue

        print(f"[PAIR] {fname} <-> {Path(red_path).name}")
        process_pair(str(orig_path), red_path)

if __name__ == "__main__":
    build_dataset()
    print("YOLO dataset built at:", OUTPUT_IMAGES, "and", OUTPUT_LABELS)
