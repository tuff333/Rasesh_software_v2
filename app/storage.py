import os
import uuid
from werkzeug.utils import secure_filename

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "output"
TEMP_DIR = "temp"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# ------------------------------------------------------------
# SAVE UPLOAD
# ------------------------------------------------------------

def save_upload(file, module="default"):
    """
    Save an uploaded PDF or image into the uploads folder.
    Returns: (filename, full_path)
    """
    fname = secure_filename(file.filename)
    ext = os.path.splitext(fname)[1]

    # Unique filename
    new_name = f"{module}_{uuid.uuid4().hex[:8]}{ext}"
    full_path = os.path.join(UPLOAD_DIR, new_name)

    file.save(full_path)
    return new_name, full_path

# ------------------------------------------------------------
# TEMP IMAGE PATH
# ------------------------------------------------------------

def temp_image_path(filename, page_num=None):
    """
    Returns a temporary image path for rendered PDF pages.
    Compatible with both old (filename only) and new (filename + page_num) usage.
    """
    base = os.path.splitext(filename)[0]
    if page_num is not None:
        name = f"{uuid.uuid4().hex[:8]}_{base}_p{page_num}.png"
    else:
        name = f"{uuid.uuid4().hex[:8]}_{base}.png"
    return os.path.join(TEMP_DIR, name)

# ------------------------------------------------------------
# SAVE OUTPUT (redacted PDF)
# ------------------------------------------------------------

def save_output(doc, original_name):
    """
    Save a redacted PDF document to the output folder.
    Returns: (filename, full_path)
    """
    base = os.path.splitext(original_name)[0]
    new_name = f"{base}_redacted_{uuid.uuid4().hex[:8]}.pdf"
    full_path = os.path.join(OUTPUT_DIR, new_name)

    doc.save(full_path)
    return new_name, full_path
