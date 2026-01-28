"""
api.py – Unified JSON response helpers for the entire backend.
Keeps all API responses consistent across invoices, manifests,
redactor, settings, and dashboard modules.
"""

from flask import jsonify


def api_ok(**kwargs):
    """
    Return a standard success JSON response.
    Example:
        return api_ok(data=..., message="Saved")
    """
    return jsonify(success=True, **kwargs)


def api_error(message, **kwargs):
    """
    Return a standard error JSON response.
    Example:
        return api_error("Invalid input", field="name")
    """
    return jsonify(success=False, error=message, **kwargs)
