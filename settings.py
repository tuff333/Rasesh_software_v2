"""
settings.py (root-level)
Legacy compatibility wrapper for the real settings system.
All logic now lives in app/services/settings.py.
"""

from app.services.settings import load_settings, save_settings

# Expose settings for old imports
settings = load_settings()
