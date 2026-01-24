# ============================================================
# TEXT EXTRACTION + REMOVAL DETECTION
# ============================================================

import fitz  # PyMuPDF

# ------------------------------------------------------------
# Extract text from PDF
# ------------------------------------------------------------
def extract_text(pdf_path):
    """Extract plain text from a PDF using PyMuPDF."""
    doc = fitz.open(pdf_path)
    try:
        pages = []
        for page in doc:
            pages.append(page.get_text())
        return "\n".join(pages)
    finally:
        doc.close()


# ------------------------------------------------------------
# Detect removed segments (A + B + D2)
# ------------------------------------------------------------
def find_removed_segments(original_text, redacted_text):
    """
    Identify removed content using:
    A) Exact removed text
    B) Full field removal
    D2) Table-like lines
    Returns raw (start, end) spans.
    """
    removed_spans = []

    orig = original_text
    red = redacted_text

    # --- Option A: exact removed words ---
    orig_words = orig.split()
    red_words = set(red.split())

    search_index = 0
    for word in orig_words:
        start = orig.find(word, search_index)
        if start == -1:
            continue
        end = start + len(word)

        if word not in red_words:
            removed_spans.append((start, end))

        search_index = end

    # --- Option B: full field removal ---
    field_keywords = [
        "Produced by", "Producer", "Client", "Name", "Address",
        "Lot", "Batch", "Certificate", "Sample", "Issued", "Received"
    ]

    for keyword in field_keywords:
        idx = orig.find(keyword)
        while idx != -1:
            line_end = orig.find("\n", idx)
            if line_end == -1:
                line_end = len(orig)

            line_text = orig[idx:line_end]

            if line_text.strip() and line_text not in red:
                removed_spans.append((idx, line_end))

            idx = orig.find(keyword, idx + 1)

    # --- Option D2: table-like lines ---
    for line in orig.split("\n"):
        if ":" in line:
            if line.strip() and line not in red:
                start = orig.find(line)
                if start != -1:
                    end = start + len(line)
                    removed_spans.append((start, end))

    return removed_spans