# ============================================================
# IMPORTS
# ============================================================
import os
import fitz  # PyMuPDF
import spacy
from spacy.tokens import DocBin
from spacy.training.example import Example
from tqdm import tqdm


# ============================================================
# GLOBAL PATHS
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_DIR = os.path.join(BASE_DIR, "training_data", "original")
REDACTED_DIR = os.path.join(BASE_DIR, "training_data", "redacted")
MODEL_DIR = os.path.join(BASE_DIR, "app", "redaction_model")

os.makedirs(MODEL_DIR, exist_ok=True)


# ============================================================
# TEXT EXTRACTION
# ============================================================
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


# ============================================================
# REMOVAL DETECTION (A + B + D2)
# ============================================================
def find_removed_segments(original_text, redacted_text):
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


# ============================================================
# SPAN CLEANING + ALIGNMENT
# ============================================================
def clean_and_align_spans(text, raw_spans):
    if not raw_spans:
        return []

    cleaned = []
    text_len = len(text)

    # Basic cleanup
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

    # Align to token boundaries
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

    # Remove duplicates + sort
    aligned = sorted(set(aligned), key=lambda x: (x[0], x[1]))

    # Remove overlaps
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

    return [(s, e, "SENSITIVE") for (s, e) in non_overlapping]


# ============================================================
# BUILD TRAINING DATASET
# ============================================================
def build_training_dataset():
    training_examples = []

    for filename in os.listdir(ORIGINAL_DIR):
        if not filename.lower().endswith(".pdf"):
            continue

        base_name = filename[:-4]
        original_path = os.path.join(ORIGINAL_DIR, filename)
        redacted_name = base_name + "_Redacted.pdf"
        redacted_path = os.path.join(REDACTED_DIR, redacted_name)

        if not os.path.exists(redacted_path):
            print(f"[WARN] No redacted file for: {filename}")
            continue

        print(f"[PAIR] {filename}  <->  {redacted_name}")

        original_text = extract_text(original_path)
        redacted_text = extract_text(redacted_path)

        raw_spans = find_removed_segments(original_text, redacted_text)
        entities = clean_and_align_spans(original_text, raw_spans)

        if not entities:
            print(f"[WARN] No valid entities found for: {filename}")
            continue

        ents_formatted = [
            {"start": s, "end": e, "label": label}
            for s, e, label in entities
        ]

        training_examples.append((original_text, {"entities": ents_formatted}))

    return training_examples


# ============================================================
# TRAIN SPACY MODEL
# ============================================================
def train_spacy_model(training_data):
    if not training_data:
        print("[ERROR] No training data available.")
        return

    print(f"[INFO] Training examples: {len(training_data)}")

    nlp = spacy.blank("en")
    ner = nlp.add_pipe("ner")
    ner.add_label("SENSITIVE")

    db = DocBin()

    for text, annot in training_data:
        doc = nlp.make_doc(text)

        valid_entities = []
        for ent in annot["entities"]:
            start = ent["start"]
            end = ent["end"]

            if not isinstance(start, int) or not isinstance(end, int):
                continue
            if start >= end:
                continue
            if start < 0 or end > len(text):
                continue
            if not text[start:end].strip():
                continue

            span = doc.char_span(start, end, label="SENSITIVE", alignment_mode="contract")
            if span is None:
                span = doc.char_span(start, end, label="SENSITIVE", alignment_mode="expand")
            if span is None:
                continue

            valid_entities.append((span.start_char, span.end_char, "SENSITIVE"))

        if not valid_entities:
            print("[WARN] Dropping example with no valid aligned entities.")
            continue

        example = Example.from_dict(doc, {"entities": valid_entities})
        db.add(example.reference)

    # Save training data ONCE
    TRAIN_DATA_PATH = os.path.join(MODEL_DIR, "training.spacy")
    db.to_disk(TRAIN_DATA_PATH)
    print(f"[INFO] Saved training data to: {TRAIN_DATA_PATH}")

    # Create config
    config_text = f"""
[nlp]
lang = "en"
pipeline = ["ner"]

[paths]
train = "{TRAIN_DATA_PATH}"
dev = "{TRAIN_DATA_PATH}"

[components]

[components.ner]
factory = "ner"

[corpora]

[corpora.train]
@readers = "spacy.Corpus.v1"
path = ${paths.train}

[corpora.dev]
@readers = "spacy.Corpus.v1"
path = ${paths.dev}

[training]
seed = 42
gpu_allocator = "pytorch"
train_corpus = "corpora.train"
dev_corpus = "corpora.dev"
max_epochs = 20
"""

    CONFIG_PATH = os.path.join(MODEL_DIR, "config.cfg")
    with open(CONFIG_PATH, "w", encoding="utf8") as f:
        f.write(config_text)

    print("[INFO] Starting spaCy training...")

    os.system(
        f"python -m spacy train {CONFIG_PATH} "
        f"--output {MODEL_DIR}"
    )

    print("[INFO] Training complete!")
    print(f"[INFO] Model saved to: {MODEL_DIR}")


# ============================================================
# MAIN ENTRY POINT
# ============================================================
def main():
    print("======================================")
    print("  TRAINING SMART REDACTION MODEL")
    print("======================================\n")

    print("[INFO] Building training dataset...")
    training_data = build_training_dataset()

    if not training_data:
        print("[ERROR] No training examples found. Check your PDF pairs.")
        return

    print(f"[INFO] Total valid training examples: {len(training_data)}\n")

    train_spacy_model(training_data)


# ============================================================
# SCRIPT START
# ============================================================
if __name__ == "__main__":
    main()