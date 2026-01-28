import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename


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

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)

    full_path = os.path.join(upload_dir, new_name)
    file.save(full_path)

    return new_name, full_path


# ------------------------------------------------------------
# TEMP IMAGE PATH (for thumbnails)
# ------------------------------------------------------------

def temp_image_path(filename, page_num=None):
    """
    Returns a temporary image path for rendered PDF pages.
    Stored in: OUTPUT_FOLDER/temp
    """
    base = os.path.splitext(filename)[0]

    if page_num is not None:
        name = f"{uuid.uuid4().hex[:8]}_{base}_p{page_num}.png"
    else:
        name = f"{uuid.uuid4().hex[:8]}_{base}.png"

    temp_dir = os.path.join(
        current_app.config["OUTPUT_FOLDER"],
        "temp"
    )
    os.makedirs(temp_dir, exist_ok=True)

    return os.path.join(temp_dir, name)
