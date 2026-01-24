# ============================================================
# DATASET BUILDER
# ============================================================

import os
from training_pipeline.text_extraction import extract_text, find_removed_segments
from training_pipeline.span_processing import clean_and_align_spans


def build_training_dataset(original_dir, redacted_dir):
    """
    Build spaCy training examples by:
    - Extracting text from original + redacted PDFs
    - Detecting removed spans
    - Cleaning + aligning spans
    - Formatting into spaCy NER training format

    Returns:
        List of (text, {"entities": [...]})
    """

    training_examples = []

    for filename in os.listdir(original_dir):
        if not filename.lower().endswith(".pdf"):
            continue

        base_name = filename[:-4]
        original_path = os.path.join(original_dir, filename)

        # Expected redacted filename
        redacted_name = base_name + "_Redacted.pdf"
        redacted_path = os.path.join(redacted_dir, redacted_name)

        if not os.path.exists(redacted_path):
            print(f"[WARN] No redacted file for: {filename}")
            continue

        print(f"[PAIR] {filename}  <->  {redacted_name}")

        # ------------------------------------------------------------
        # EXTRACT TEXT
        # ------------------------------------------------------------
        original_text = extract_text(original_path)
        redacted_text = extract_text(redacted_path)

        # ------------------------------------------------------------
        # FIND REMOVED SEGMENTS
        # ------------------------------------------------------------
        raw_spans = find_removed_segments(original_text, redacted_text)

        # ------------------------------------------------------------
        # CLEAN + ALIGN SPANS
        # ------------------------------------------------------------
        entities = clean_and_align_spans(original_text, raw_spans)

        if not entities:
            print(f"[WARN] No valid entities found for: {filename}")
            continue

        # ------------------------------------------------------------
        # FORMAT ENTITIES FOR SPACY
        # ------------------------------------------------------------
        ents_formatted = [
            {"start": s, "end": e, "label": label}
            for s, e, label in entities
        ]

        training_examples.append((original_text, {"entities": ents_formatted}))

    return training_examples