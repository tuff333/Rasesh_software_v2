# ============================================================
# MASTER TRAINING ORCHESTRATOR (Unified spaCy Pipeline)
# ============================================================

import os
from pathlib import Path

# Import from the local spacy_pipeline package
from .dataset_builder import build_training_dataset
from .model_trainer import train_spacy_model


def main():
    print("======================================")
    print("   SMART REDACTION MODEL TRAINING")
    print("======================================\n")

    # ------------------------------------------------------------
    # PATH SETUP (relative to ...\Ai)
    # ------------------------------------------------------------
    BASE_DIR = Path(__file__).resolve().parents[2]   # ...\Ai
    TRAINING_DATA = BASE_DIR / "training_data"
    TRAINED_MODEL = BASE_DIR / "trained_model" / "spacy"

    ORIGINAL_DIR = TRAINING_DATA / "original"
    REDACTED_DIR = TRAINING_DATA / "redacted"

    TRAINED_MODEL.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Original PDFs: {ORIGINAL_DIR}")
    print(f"[INFO] Redacted PDFs: {REDACTED_DIR}")
    print(f"[INFO] Model output:  {TRAINED_MODEL}\n")

    # ------------------------------------------------------------
    # BUILD TRAINING DATASET
    # ------------------------------------------------------------
    print("[INFO] Building training dataset...")
    training_data = build_training_dataset(str(ORIGINAL_DIR), str(REDACTED_DIR))

    if not training_data:
        print("[ERROR] No training examples found. Check your PDF pairs.")
        return

    print(f"[INFO] Total valid training examples: {len(training_data)}\n")

    # ------------------------------------------------------------
    # TRAIN MODEL
    # ------------------------------------------------------------
    train_spacy_model(training_data, str(TRAINED_MODEL))

    print("\n✔ spaCy training complete.")
    print(f"✔ Model saved to: {TRAINED_MODEL}")

# ------------------------------------------------------------
# SCRIPT ENTRY POINT
# ------------------------------------------------------------
if __name__ == "__main__":
    main()
