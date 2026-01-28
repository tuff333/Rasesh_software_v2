"""
path.py – Rasesh IM PDF CRM
Centralized path helpers using Flask app configuration.
"""

import os
from flask import current_app


def base_dir():
    """Return the application's base directory."""
    return current_app.config["BASE_DIR"]


def upload_folder():
    """Return the uploads folder path."""
    return current_app.config["UPLOAD_FOLDER"]


def output_folder():
    """Return the output folder path."""
    return current_app.config["OUTPUT_FOLDER"]


def database_file():
    """Return the database file path."""
    return current_app.config["DATABASE"]


def ensure_directories():
    """Ensure core folders exist."""
    for key in ["UPLOAD_FOLDER", "OUTPUT_FOLDER"]:
        folder = current_app.config[key]
        os.makedirs(folder, exist_ok=True)
