import subprocess
import sys
from pathlib import Path

# BASE_DIR = ...\Ai
BASE_DIR = Path(__file__).resolve().parents[1]

TRAINING_BACKEND = BASE_DIR / "training_backend"
TRAINED_MODEL = BASE_DIR / "trained_model"

def ensure_dirs():
    (TRAINED_MODEL / "spacy").mkdir(parents=True, exist_ok=True)
    (TRAINED_MODEL / "yolo").mkdir(parents=True, exist_ok=True)

def run_spacy():
    cmd = [sys.executable, "-m", "spacy_pipeline.master"]
    subprocess.check_call(cmd, cwd=TRAINING_BACKEND)

def run_yolo():
    yolo_dir = TRAINING_BACKEND / "yolo_pipeline"
    cmd = [sys.executable, "train_yolo.py"]
    subprocess.check_call(cmd, cwd=yolo_dir)

if __name__ == "__main__":
    ensure_dirs()
    print("Running spaCy training...")
    run_spacy()
    print("Running YOLO training...")
    run_yolo()
    print("All training complete.")
