import json
import os

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "theme": "light",
    "upload_folder": "redaction",
    "ocr_default": False,
    "zoom_mode": "fit-width",
    "show_tips": True,

    "output_redactions": "output/redactions",
    "output_invoices": "output/invoices",
    "output_manifests": "output/manifests",

    "shortcuts": {
        "prev_page": "ArrowLeft",
        "next_page": "ArrowRight",
        "undo": "Ctrl+Z",
        "clear": "Delete",
        "apply": "Ctrl+S",
        "zoom_in": "Ctrl+Plus",
        "zoom_out": "Ctrl+Minus",
        "zoom_reset": "Ctrl+0",
        "toggle_thumbs": "Ctrl+Shift+W",
        "toggle_ocr": "Ctrl+Shift+O"
    }
}


def load_settings():
    """Load settings from JSON file or create defaults."""
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS

    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except:
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS


def save_settings(data):
    """Save settings to JSON file."""
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)


# Load once at startup
settings = load_settings()
