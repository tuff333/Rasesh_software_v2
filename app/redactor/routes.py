import os
import sqlite3
import json
import fitz
from datetime import datetime
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


def ensure_templates_table(conn):
    """Ensure the redaction_templates table exists."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS redaction_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT,
            doc_type TEXT,
            boxes_json TEXT NOT NULL,
            created_at TEXT
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

    pdf_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    try:
        doc = fitz.open(pdf_path)
        pages = doc.page_count
        doc.close()
    except Exception:
        pages = 1

    return render_template("redactor/viewer.html", filename=filename, pages=pages)


@redactor_bp.route("/get_page/<filename>/<int:p>")
def get_page(filename, p):
    pdf_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    out = render_page(pdf_path, p)
    if not out:
        return api_error("Invalid page")
    return send_file(out, mimetype="image/png")


# ------------------------------------------------------------
# SUGGESTIONS (AI + OCR FLAG)
# ------------------------------------------------------------
@redactor_bp.route("/suggestions/<filename>")
def suggestions(filename):
    pdf_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    ocr_flag = request.args.get("ocr", "0")
    use_ocr = ocr_flag == "1"
    sugg = extract_suggestions(pdf_path, use_ocr=use_ocr)
    return api_ok(suggestions=sugg)


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


# ------------------------------------------------------------
# REDACTION TEMPLATES
# ------------------------------------------------------------
@redactor_bp.route("/template/save", methods=["POST"])
def template_save():
    """
    Save a redaction template based on current preview boxes.
    JSON body:
      {
        "filename": "...",
        "name": "Template Name",
        "company": "Amazon",
        "doc_type": "Invoice"
      }
    """
    data = request.json or {}
    filename = data.get("filename")
    name = data.get("name")
    company = data.get("company")
    doc_type = data.get("doc_type")

    if not filename or not name:
        return api_error("Filename and template name are required")

    with get_conn() as conn:
        ensure_preview_table(conn)
        ensure_templates_table(conn)

        rows = conn.execute(
            """
            SELECT page, x, y, width, height, type, text
            FROM redaction_preview
            WHERE filename=?
            ORDER BY id ASC
            """,
            (filename,),
        ).fetchall()

        boxes = [
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

        if not boxes:
            return api_error("No preview boxes to save as template")

        boxes_json = json.dumps(boxes)
        ts = datetime.now().isoformat(timespec="seconds")

        conn.execute(
            """
            INSERT INTO redaction_templates (name, company, doc_type, boxes_json, created_at)
            VALUES (?,?,?,?,?)
            """,
            (name, company, doc_type, boxes_json, ts),
        )
        conn.commit()

    return api_ok(message="Template saved")


@redactor_bp.route("/template/list")
def template_list():
    """
    List templates, optionally filtered by company and doc_type.
    Query params:
      ?company=Amazon&doc_type=Invoice
    """
    company = request.args.get("company")
    doc_type = request.args.get("doc_type")

    with get_conn() as conn:
        ensure_templates_table(conn)

        query = "SELECT id, name, company, doc_type, created_at FROM redaction_templates WHERE 1=1"
        params = []

        if company:
            query += " AND (company = ? OR company IS NULL OR company = '')"
            params.append(company)

        if doc_type:
            query += " AND (doc_type = ? OR doc_type IS NULL OR doc_type = '')"
            params.append(doc_type)

        query += " ORDER BY created_at DESC"

        rows = conn.execute(query, params).fetchall()

    templates = [
        {
            "id": r["id"],
            "name": r["name"],
            "company": r["company"],
            "doc_type": r["doc_type"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]

    return api_ok(templates=templates)


@redactor_bp.route("/template/apply", methods=["POST"])
def template_apply():
    """
    Apply a template to the current document.
    JSON body:
      {
        "filename": "...",
        "template_id": 1,
        "mode": "all" or "page",
        "page": 0   # required if mode == "page"
      }
    """
    data = request.json or {}
    filename = data.get("filename")
    template_id = data.get("template_id")
    mode = data.get("mode", "all")
    page = data.get("page", 0)

    if not filename or not template_id:
        return api_error("filename and template_id are required")

    with get_conn() as conn:
        ensure_preview_table(conn)
        ensure_templates_table(conn)

        row = conn.execute(
            "SELECT boxes_json FROM redaction_templates WHERE id=?",
            (template_id,),
        ).fetchone()

        if not row:
            return api_error("Template not found")

        try:
            boxes = json.loads(row["boxes_json"])
        except Exception:
            return api_error("Invalid template data")

        new_boxes = []

        if mode == "all":
            # Apply boxes exactly as stored (respect original pages)
            for b in boxes:
                new_boxes.append(
                    (
                        filename,
                        b.get("page", 0),
                        b.get("x", 0.0),
                        b.get("y", 0.0),
                        b.get("width", 0.0),
                        b.get("height", 0.0),
                        b.get("type", "area"),
                        b.get("text"),
                    )
                )
        else:
            # mode == "page": apply all boxes to the given page
            for b in boxes:
                new_boxes.append(
                    (
                        filename,
                        page,
                        b.get("x", 0.0),
                        b.get("y", 0.0),
                        b.get("width", 0.0),
                        b.get("height", 0.0),
                        b.get("type", "area"),
                        b.get("text"),
                    )
                )

        if not new_boxes:
            return api_error("No boxes to apply from template")

        conn.executemany(
            """
            INSERT INTO redaction_preview
                (filename, page, x, y, width, height, type, text)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            new_boxes,
        )
        conn.commit()

    return api_ok(message="Template applied")
