# ============================================================
# MODEL TRAINER
# ============================================================

import os
import spacy
from spacy.tokens import DocBin
from spacy.training.example import Example


def train_spacy_model(training_data, model_dir):
    """
    Train a spaCy NER model using the cleaned training dataset.
    Saves:
        - training.spacy
        - config.cfg
        - model-best/
    """

    if not training_data:
        print("[ERROR] No training data available.")
        return

    print(f"[INFO] Training examples: {len(training_data)}")

    # ------------------------------------------------------------
    # CREATE BLANK MODEL + NER PIPELINE
    # ------------------------------------------------------------
    nlp = spacy.blank("en")
    ner = nlp.add_pipe("ner")
    ner.add_label("SENSITIVE")

    # ------------------------------------------------------------
    # BUILD DOCBIN
    # ------------------------------------------------------------
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

    # ------------------------------------------------------------
    # SAVE TRAINING DATA
    # ------------------------------------------------------------
    TRAIN_DIR = os.path.join(model_dir, "training")
    os.makedirs(TRAIN_DIR, exist_ok=True)

    TRAIN_DATA_PATH = os.path.join(TRAIN_DIR, "train.spacy")
    db.to_disk(TRAIN_DATA_PATH)
    print(f"[INFO] Saved training data to: {TRAIN_DATA_PATH}")

    # ------------------------------------------------------------
    # CREATE CONFIG
    # ------------------------------------------------------------
    config_text = f"""
[nlp]
lang = "en"
pipeline = ["ner"]

[paths]
train = {TRAIN_DIR}
dev = {TRAIN_DIR}

[components]

[components.ner]
factory = "ner"

[corpora]

[corpora.train]
@readers = "spacy.Corpus.v1"
path = ${{paths.train}}

[corpora.dev]
@readers = "spacy.Corpus.v1"
path = ${{paths.dev}}

[training]
seed = 42
gpu_allocator = "pytorch"
train_corpus = "corpora.train"
dev_corpus = "corpora.dev"
max_epochs = 20
"""

    CONFIG_PATH = os.path.join(model_dir, "config.cfg")
    with open(CONFIG_PATH, "w", encoding="utf8") as f:
        f.write(config_text)

    print("[INFO] Starting spaCy training...")

    # ------------------------------------------------------------
    # RUN TRAINING
    # ------------------------------------------------------------
    os.system(
        f"python -m spacy train {CONFIG_PATH} "
        f"--output {model_dir}"
    )

    print("[INFO] Training complete!")
    print(f"[INFO] Model saved to: {model_dir}")