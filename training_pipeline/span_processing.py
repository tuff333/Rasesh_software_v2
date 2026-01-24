# ============================================================
# SPAN CLEANING + ALIGNMENT
# ============================================================

import spacy


def clean_and_align_spans(text, raw_spans):
    """
    Clean raw spans:
    - Ensure valid bounds
    - Remove whitespace-only spans
    - Align to token boundaries
    - Remove overlaps
    Returns: list of (start, end, "SENSITIVE")
    """
    if not raw_spans:
        return []

    cleaned = []
    text_len = len(text)

    # ------------------------------------------------------------
    # BASIC CLEANUP
    # ------------------------------------------------------------
    for start, end in raw_spans:
        if start is None or end is None:
            continue
        if not (0 <= start < end <= text_len):
            continue
        if not text[start:end].strip():
            continue
        cleaned.append((start, end))

    if not cleaned:
        return []

    # ------------------------------------------------------------
    # ALIGN TO TOKEN BOUNDARIES
    # ------------------------------------------------------------
    nlp_tmp = spacy.blank("en")
    doc = nlp_tmp.make_doc(text)

    aligned = []
    for start, end in cleaned:
        span = doc.char_span(start, end, label="SENSITIVE", alignment_mode="contract")
        if span is None:
            span = doc.char_span(start, end, label="SENSITIVE", alignment_mode="expand")
        if span is None:
            continue
        aligned.append((span.start_char, span.end_char))

    if not aligned:
        return []

    # ------------------------------------------------------------
    # REMOVE DUPLICATES + SORT
    # ------------------------------------------------------------
    aligned = sorted(set(aligned), key=lambda x: (x[0], x[1]))

    # ------------------------------------------------------------
    # REMOVE OVERLAPPING SPANS
    # ------------------------------------------------------------
    non_overlapping = []
    last_start, last_end = -1, -1

    for start, end in aligned:
        if start >= last_end:
            non_overlapping.append((start, end))
            last_start, last_end = start, end
        else:
            prev_start, prev_end = non_overlapping[-1]
            if (end - start) > (prev_end - prev_start):
                non_overlapping[-1] = (start, end)
                last_start, last_end = start, end

    # ------------------------------------------------------------
    # RETURN LABELED SPANS
    # ------------------------------------------------------------
    return [(s, e, "SENSITIVE") for (s, e) in non_overlapping]