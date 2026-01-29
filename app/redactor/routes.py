import os
import sqlite3
import fitz
from flask import (
    request,
    render_template,
    send_file,
    url_for,
    current_app,
)
from app.redactor import redactor_bp
from app.storage import save_upload
from app.services.api import api_ok, api_error
from app.services.pdf import render_page
from app.services.suggestions import extract_suggestions
from app.services.redaction import apply_redactions
from app.services.history import log_redaction
from app.state.workspace import (
    open_document,
    list_documents,
    set_active,
    close_document,
)


def get_conn():
    """Return a SQLite connection using the app's configured DB path."""
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_preview_table(conn):
    """Ensure the redaction_preview table exists."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS redaction_preview (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            page INTEGER,
            x REAL,
            y REAL,
            width REAL,
            height REAL,
            type TEXT,
            text TEXT
        )
        """
    )


# ------------------------------------------------------------
# UPLOAD PAGE (GET)
# ------------------------------------------------------------
@redactor_bp.route("/", methods=["GET"])
def upload_page():
    """Render the main PDF redaction upload page."""
    return render_template("redactor/upload.html")


# ------------------------------------------------------------
# UPLOAD (API)
# ------------------------------------------------------------
@redactor_bp.route("/upload", methods=["POST"])
def upload_pdf():
    file = request.files.get("pdf")
    if not file:
        return api_error("No file uploaded")

    module = request.args.get("module", "default")
    fname, path = save_upload(file, module=module)

    try:
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
    pdf_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    out = render_page(pdf_path, p)
    if not out:
        return api_error("Invalid page")
    return send_file(out, mimetype="image/png")


# ------------------------------------------------------------
# SUGGESTIONS
# ------------------------------------------------------------
@redactor_bp.route("/suggestions/<filename>")
def suggestions(filename):
    pdf_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    return api_ok(suggestions=extract_suggestions(pdf_path))


# ------------------------------------------------------------
# PREVIEW MODE
# ------------------------------------------------------------
@redactor_bp.route("/preview/save", methods=["POST"])
def preview_save():
    data = request.json
    filename = data["filename"]
    changes = data["changes"]

    with get_conn() as conn:
        ensure_preview_table(conn)
        for ch in changes:
            conn.execute(
                """
                INSERT INTO redaction_preview
                    (filename, page, x, y, width, height, type, text)
                VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    filename,
                    ch["page"],
                    ch["x"],
                    ch["y"],
                    ch["width"],
                    ch["height"],
                    ch["type"],
                    ch.get("text"),
                ),
            )
        conn.commit()

    return api_ok()


@redactor_bp.route("/preview/load/<filename>")
def preview_load(filename):
    with get_conn() as conn:
        ensure_preview_table(conn)
        rows = conn.execute(
            """
            SELECT page, x, y, width, height, type, text
            FROM redaction_preview
            WHERE filename=?
            ORDER BY id ASC
            """,
            (filename,),
        ).fetchall()

    preview = [
        {
            "page": r["page"],
            "x": r["x"],
            "y": r["y"],
            "width": r["width"],
            "height": r["height"],
            "type": r["type"],
            "text": r["text"],
        }
        for r in rows
    ]

    return api_ok(preview=preview)


@redactor_bp.route("/preview/undo", methods=["POST"])
def preview_undo():
    filename = request.json["filename"]

    with get_conn() as conn:
        ensure_preview_table(conn)
        conn.execute(
            """
            DELETE FROM redaction_preview
            WHERE id = (
                SELECT id FROM redaction_preview
                WHERE filename=?
                ORDER BY id DESC
                LIMIT 1
            )
            """,
            (filename,),
        )
        conn.commit()

    return api_ok()


@redactor_bp.route("/preview/clear", methods=["POST"])
def preview_clear():
    filename = request.json["filename"]

    with get_conn() as conn:
        ensure_preview_table(conn)
        conn.execute("DELETE FROM redaction_preview WHERE filename=?", (filename,))
        conn.commit()

    return api_ok()


# ------------------------------------------------------------
# APPLY PREVIEW
# ------------------------------------------------------------
@redactor_bp.route("/apply_preview", methods=["POST"])
def apply_preview():
    filename = request.json["filename"]
    orig = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)

    with get_conn() as conn:
        ensure_preview_table(conn)
        rows = conn.execute(
            """
            SELECT page, x, y, width, height, type, text
            FROM redaction_preview
            WHERE filename=?
            ORDER BY id ASC
            """,
            (filename,),
        ).fetchall()

    changes = [
        {
            "page": r["page"],
            "x": r["x"],
            "y": r["y"],
            "width": r["width"],
            "height": r["height"],
            "type": r["type"],
            "text": r["text"],
        }
        for r in rows
    ]

    out_name, out_path = apply_redactions(orig, changes)
    if not out_name:
        return api_error("Redaction failed")

    log_redaction(filename, out_name, changes)

    with get_conn() as conn:
        ensure_preview_table(conn)
        conn.execute("DELETE FROM redaction_preview WHERE filename=?", (filename,))
        conn.commit()

    return api_ok(download_url=url_for("redactor.download", filename=out_name))


# ------------------------------------------------------------
# DOWNLOAD
# ------------------------------------------------------------
@redactor_bp.route("/download/<filename>")
def download(filename):
    path = os.path.join(
        current_app.config["OUTPUT_FOLDER"],
        "redactions",
        filename,
    )
    return send_file(path, as_attachment=True)


# ------------------------------------------------------------
# THUMBNAILS
# ------------------------------------------------------------
@redactor_bp.route("/thumbnail/<filename>/<int:p>")
def thumbnail(filename, p):
    pdf_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    out = render_page(pdf_path, p, dpi=60)

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


@redactor_bp.route("/workspace/open", methods=["POST"])
def workspace_open():
    """Open or register the current document in the workspace."""
    data = request.json or {}
    filename = data.get("filename")
    display_name = data.get("display_name", filename)

    if not filename:
        return api_error("No filename provided")

    open_document(filename, display_name)
    return api_ok()
