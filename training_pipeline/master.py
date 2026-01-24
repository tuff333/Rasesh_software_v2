# ============================================================
# MASTER TRAINING ORCHESTRATOR
# ============================================================

import os

from training_pipeline.dataset_builder import build_training_dataset
from training_pipeline.model_trainer import train_spacy_model


def main():
    print("======================================")
    print("   SMART REDACTION MODEL TRAINING")
    print("======================================\n")

    # ------------------------------------------------------------
    # DEFINE PATHS
    # ------------------------------------------------------------
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    ORIGINAL_DIR = os.path.join(BASE_DIR, "training_data", "original")
    REDACTED_DIR = os.path.join(BASE_DIR, "training_data", "redacted")
    MODEL_DIR = os.path.join(BASE_DIR, "app", "redaction_model")

    print(f"[INFO] Original PDFs: {ORIGINAL_DIR}")
    print(f"[INFO] Redacted PDFs: {REDACTED_DIR}")
    print(f"[INFO] Model output:  {MODEL_DIR}\n")

    # ------------------------------------------------------------
    # BUILD TRAINING DATASET
    # ------------------------------------------------------------
    print("[INFO] Building training dataset...")
    training_data = build_training_dataset(ORIGINAL_DIR, REDACTED_DIR)

    if not training_data:
        print("[ERROR] No training examples found. Check your PDF pairs.")
        return

    print(f"[INFO] Total valid training examples: {len(training_data)}\n")

    # ------------------------------------------------------------
    # TRAIN MODEL
    # ------------------------------------------------------------
    train_spacy_model(training_data, MODEL_DIR)


# ------------------------------------------------------------
# SCRIPT ENTRY POINT
# ------------------------------------------------------------
if __name__ == "__main__":
    main()