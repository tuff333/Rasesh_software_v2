from werkzeug.utils import secure_filename


def safe_filename(original_name):
    """Return a secure, sanitized filename."""
    return secure_filename(original_name)
