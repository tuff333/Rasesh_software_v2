import os
import json
from flask import Blueprint, jsonify, request, current_app

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")

# Path to settings.json
def settings_file():
    return os.path.join(current_app.config["BASE_DIR"], "settings.json")


# Default settings structure
DEFAULT_SETTINGS = {
    "theme": "light",
    "upload_folder": "redaction",
    "ocr_default": False,
    "zoom_mode": "fit-width",
    "show_tips": True,

    "output_redactions": "output/redactions",
    "output_invoices": "output/invoices",
    "output_manifests": "output/manifests",

    # -------------------------
    # NEW: Invoice Settings
    # -------------------------
    "default_template": "classic",
    "default_signature_id": "",
    "default_gst": "",

    # -------------------------
    # NEW: Email Settings
    # -------------------------
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_username": "",
    "smtp_password": "",
    "smtp_from": "",

    # -------------------------
    # Shortcuts
    # -------------------------
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


def merge_defaults(existing):
    """
    Ensures new settings keys are added automatically
    without overwriting user values.
    """
    updated = dict(existing)

    for key, value in DEFAULT_SETTINGS.items():
        if key not in updated:
            updated[key] = value

        # Handle nested dicts (shortcuts)
        if isinstance(value, dict):
            if key not in updated or not isinstance(updated[key], dict):
                updated[key] = value
            else:
                for subkey, subval in value.items():
                    if subkey not in updated[key]:
                        updated[key][subkey] = subval

    return updated


def load_settings():
    """Load settings.json or create defaults."""
    path = settings_file()

    if not os.path.exists(path):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS

    try:
        with open(path, "r") as f:
            data = json.load(f)
    except Exception:
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS

    # Merge new defaults without overwriting user settings
    merged = merge_defaults(data)
    save_settings(merged)
    return merged


def save_settings(data):
    """Save settings.json."""
    path = settings_file()
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


# -------------------------
# API ROUTES
# -------------------------

@settings_bp.get("/data")
def api_get_settings():
    return jsonify(load_settings())


@settings_bp.post("/save")
def api_save_settings():
    data = request.json
    save_settings(data)
    return jsonify({"success": True})
