from ultralytics import YOLO
from pathlib import Path

# BASE_DIR = ...\Ai
BASE_DIR = Path(__file__).resolve().parents[2]

TRAINING_DATA = BASE_DIR / "training_data"
TRAINED_MODEL = BASE_DIR / "trained_model" / "yolo"
PIPELINE_DIR = Path(__file__).resolve().parent

DATA_YAML = PIPELINE_DIR / "data.yaml"
PRETRAINED = PIPELINE_DIR / "yolov8n.pt"

def main():
    TRAINED_MODEL.mkdir(parents=True, exist_ok=True)

    print("📌 Training data:", TRAINING_DATA)
    print("📌 Using data.yaml:", DATA_YAML)
    print("📌 Saving YOLO models to:", TRAINED_MODEL)

    model = YOLO(str(PRETRAINED))

    model.train(
        data=str(DATA_YAML),
        epochs=50,
        imgsz=1024,
        project=str(TRAINED_MODEL),
        name="sensitive_yolo",
        batch=8,
    )

    print("\n✔ YOLO training complete.")
    print(f"✔ Models saved to: {TRAINED_MODEL}")

if __name__ == "__main__":
    main()
