from flask import request, jsonify, render_template, send_file, url_for
import os
from app.redactor import redactor_bp
from app.storage import save_upload, temp_image_path, save_output
from app.services.api import api_ok, api_error
from app.services.pdf import render_page
from app.services.suggestions import extract_suggestions
from app.services.redaction import apply_redactions
from app.services.history import log_redaction
from app.state.workspace import open_document, list_documents, set_active, close_document
from app.database import DB_PATH
import sqlite3

# ------------------------------------------------------------
# UPLOAD
# ------------------------------------------------------------

@redactor_bp.route("/upload", methods=["POST"])
def upload_pdf():
    file = request.files.get("pdf")
    if not file:
        return api_error("No file uploaded")

    # Read module from frontend (default = "default")
    module = request.args.get("module", "default")

    # Save file in correct folder
    fname, path = save_upload(file, module=module)

    try:
        import fitz
        doc = fitz.open(path)
        pages = doc.page_count
        text_preview = "".join(p.get_text() for p in doc)[:1000]
        doc.close()
    except Exception as e:
        return api_error(str(e))

    return api_ok(filename=fname, pages=pages, text_preview=text_preview)

# ------------------------------------------------------------
# VIEWER
# ------------------------------------------------------------

@redactor_bp.route("/viewer/<filename>")
def viewer(filename):
    open_document(filename, filename)
    return render_template("redactor/viewer.html", filename=filename)


@redactor_bp.route("/get_page/<filename>/<int:p>")
def get_page(filename, p):
    path = os.path.join("uploads", filename)
    out = render_page(path, p)
    if not out:
        return api_error("Invalid page")
    return send_file(out, mimetype="image/png")


# ------------------------------------------------------------
# SUGGESTIONS
# ------------------------------------------------------------

@redactor_bp.route("/suggestions/<filename>")
def suggestions(filename):
    path = os.path.join("uploads", filename)
    return api_ok(suggestions=extract_suggestions(path))


# ------------------------------------------------------------
# PREVIEW MODE
# ------------------------------------------------------------

@redactor_bp.route("/preview/save", methods=["POST"])
def preview_save():
    data = request.json
    filename = data["filename"]
    changes = data["changes"]

    with sqlite3.connect(DB_PATH) as conn:
        for ch in changes:
            conn.execute('''
                INSERT INTO redaction_preview(filename, page, x, y, width, height, type, text)
                VALUES(?,?,?,?,?,?,?,?)
            ''', (
                filename,
                ch["page"],
                ch["x"],
                ch["y"],
                ch["width"],
                ch["height"],
                ch["type"],
                ch.get("text")
            ))
        conn.commit()

    return api_ok()


@redactor_bp.route("/preview/load/<filename>")
def preview_load(filename):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute('''
            SELECT page, x, y, width, height, type, text
            FROM redaction_preview
            WHERE filename=?
            ORDER BY id ASC
        ''', (filename,)).fetchall()

    preview = [
        {
            "page": r[0],
            "x": r[1],
            "y": r[2],
            "width": r[3],
            "height": r[4],
            "type": r[5],
            "text": r[6]
        }
        for r in rows
    ]

    return api_ok(preview=preview)


@redactor_bp.route("/preview/undo", methods=["POST"])
def preview_undo():
    filename = request.json["filename"]

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            DELETE FROM redaction_preview
            WHERE id = (
                SELECT id FROM redaction_preview
                WHERE filename=?
                ORDER BY id DESC
                LIMIT 1
            )
        ''', (filename,))
        conn.commit()

    return api_ok()


@redactor_bp.route("/preview/clear", methods=["POST"])
def preview_clear():
    filename = request.json["filename"]

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM redaction_preview WHERE filename=?", (filename,))
        conn.commit()

    return api_ok()


# ------------------------------------------------------------
# APPLY PREVIEW
# ------------------------------------------------------------

@redactor_bp.route("/apply_preview", methods=["POST"])
def apply_preview():
    filename = request.json["filename"]
    orig = os.path.join("uploads", filename)

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute('''
            SELECT page, x, y, width, height, type, text
            FROM redaction_preview
            WHERE filename=?
            ORDER BY id ASC
        ''', (filename,)).fetchall()

    changes = [
        {
            "page": r[0],
            "x": r[1],
            "y": r[2],
            "width": r[3],
            "height": r[4],
            "type": r[5],
            "text": r[6]
        }
        for r in rows
    ]

    doc = apply_redactions(orig, changes)
    out_name, out_path = save_output(doc, filename)
    doc.close()

    log_redaction(filename, out_name, changes)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM redaction_preview WHERE filename=?", (filename,))
        conn.commit()

    return api_ok(download_url=url_for("redactor.download", filename=out_name))


@redactor_bp.route("/download/<filename>")
def download(filename):
    return send_file(os.path.join("output", filename), as_attachment=True)


@redactor_bp.route("/thumbnail/<filename>/<int:p>")
def thumbnail(filename, p):
    from app.services.pdf import render_page

    # Low DPI for thumbnails
    path = os.path.join("uploads", filename)
    out = render_page(path, p, dpi=60)

    if not out:
        return api_error("Invalid page")

    return send_file(out, mimetype="image/png")


# ------------------------------------------------------------
# WORKSPACE
# ------------------------------------------------------------

@redactor_bp.route("/workspace/list")
def workspace_list():
    return api_ok(documents=list_documents())


@redactor_bp.route("/workspace/set_active", methods=["POST"])
def workspace_set_active():
    set_active(request.json["filename"])
    return api_ok()


@redactor_bp.route("/workspace/close", methods=["POST"])
def workspace_close():
    close_document(request.json["filename"])
    return api_ok()
