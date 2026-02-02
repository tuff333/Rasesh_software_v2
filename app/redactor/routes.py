import os
import sqlite3
import json
import fitz
from io import BytesIO
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


def ensure_template_versions_table(conn):
    """Ensure the redaction_template_versions table exists."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS redaction_template_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            version INTEGER NOT NULL,
            name TEXT,
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
# SUGGESTIONS (AI + OCR FLAG + CONFIDENCE FILTER)
# ------------------------------------------------------------
@redactor_bp.route("/suggestions/<filename>")
def suggestions(filename):
    """
    Return AI suggestions for a PDF.

    Query params:
      ?ocr=0|1           -> enable OCR fusion into spaCy text
      ?min_conf=0.0-1.0  -> filter YOLO suggestions by confidence
    """
    pdf_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)

    ocr_flag = request.args.get("ocr", "0")
    use_ocr = ocr_flag == "1"

    min_conf_str = request.args.get("min_conf", "").strip()
    try:
        min_conf = float(min_conf_str) if min_conf_str else 0.0
    except ValueError:
        min_conf = 0.0

    sugg = extract_suggestions(
        pdf_path,
        use_ocr=use_ocr,
        min_conf=min_conf,
    )
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
# REDACTION TEMPLATES — BASE
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
        ensure_template_versions_table(conn)

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

        cur = conn.execute(
            """
            INSERT INTO redaction_templates (name, company, doc_type, boxes_json, created_at)
            VALUES (?,?,?,?,?)
            """,
            (name, company, doc_type, boxes_json, ts),
        )
        template_id = cur.lastrowid

        # initial version 1
        conn.execute(
            """
            INSERT INTO redaction_template_versions
                (template_id, version, name, company, doc_type, boxes_json, created_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (template_id, 1, name, company, doc_type, boxes_json, ts),
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


@redactor_bp.route("/template/load/<int:template_id>")
def template_load(template_id):
    """
    Load a template's boxes for editing.
    """
    with get_conn() as conn:
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

    return api_ok(boxes=boxes)


@redactor_bp.route("/template/update", methods=["POST"])
def template_update():
    """
    Overwrite an existing template with the current preview boxes.
    JSON body:
      {
        "template_id": 1,
        "filename": "redaction_1234.pdf"
      }
    """
    data = request.json or {}
    template_id = data.get("template_id")
    filename = data.get("filename")

    if not template_id or not filename:
        return api_error("template_id and filename required")

    with get_conn() as conn:
        ensure_preview_table(conn)
        ensure_templates_table(conn)
        ensure_template_versions_table(conn)

        # current template (for versioning)
        cur_tpl = conn.execute(
            "SELECT name, company, doc_type, boxes_json, created_at FROM redaction_templates WHERE id=?",
            (template_id,),
        ).fetchone()
        if not cur_tpl:
            return api_error("Template not found")

        # compute next version
        row_ver = conn.execute(
            "SELECT MAX(version) AS v FROM redaction_template_versions WHERE template_id=?",
            (template_id,),
        ).fetchone()
        next_version = (row_ver["v"] or 1) + 1

        # store old version
        conn.execute(
            """
            INSERT INTO redaction_template_versions
                (template_id, version, name, company, doc_type, boxes_json, created_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                template_id,
                next_version,
                cur_tpl["name"],
                cur_tpl["company"],
                cur_tpl["doc_type"],
                cur_tpl["boxes_json"],
                cur_tpl["created_at"],
            ),
        )

        # now overwrite with current preview
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
            return api_error("No preview boxes to save")

        boxes_json = json.dumps(boxes)
        ts = datetime.now().isoformat(timespec="seconds")

        conn.execute(
            "UPDATE redaction_templates SET boxes_json=?, created_at=? WHERE id=?",
            (boxes_json, ts, template_id),
        )
        conn.commit()

    return api_ok(message="Template updated")


# ------------------------------------------------------------
# REDACTION TEMPLATES — AUTO-DETECT COMPANY/DOC TYPE
# ------------------------------------------------------------
@redactor_bp.route("/template/auto_detect/<filename>")
def template_auto_detect(filename):
    """
    Simple heuristic to auto-detect company and doc_type from PDF text.
    """
    pdf_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(pdf_path):
        return api_error("File not found")

    try:
        doc = fitz.open(pdf_path)
        text = ""
        if doc.page_count > 0:
            text = doc[0].get_text()[:5000]
        doc.close()
    except Exception as e:
        return api_error(str(e))

    text_lower = text.lower()

    company = ""
    doc_type = ""

    # naive company detection
    known_companies = ["amazon", "ups", "fedex", "dhl", "walmart", "costco", "google", "microsoft"]
    for c in known_companies:
        if c in text_lower:
            company = c.capitalize()
            break

    # naive doc_type detection
    if "invoice" in text_lower:
        doc_type = "Invoice"
    elif "statement" in text_lower:
        doc_type = "Statement"
    elif "receipt" in text_lower:
        doc_type = "Receipt"
    elif "bill of lading" in text_lower:
        doc_type = "Bill of Lading"

    return api_ok(company=company, doc_type=doc_type)


# ------------------------------------------------------------
# REDACTION TEMPLATES — VERSIONS
# ------------------------------------------------------------
@redactor_bp.route("/template/versions/<int:template_id>")
def template_versions(template_id):
    """
    List versions for a template.
    """
    with get_conn() as conn:
        ensure_template_versions_table(conn)
        rows = conn.execute(
            """
            SELECT id, version, created_at
            FROM redaction_template_versions
            WHERE template_id=?
            ORDER BY version DESC
            """,
            (template_id,),
        ).fetchall()

    versions = [
        {
            "id": r["id"],
            "version": r["version"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]

    return api_ok(versions=versions)


# ------------------------------------------------------------
# REDACTION TEMPLATES — EXPORT / IMPORT
# ------------------------------------------------------------
@redactor_bp.route("/template/export/<int:template_id>")
def template_export(template_id):
    """
    Export a template as a JSON file.
    """
    with get_conn() as conn:
        ensure_templates_table(conn)
        row = conn.execute(
            """
            SELECT id, name, company, doc_type, boxes_json, created_at
            FROM redaction_templates
            WHERE id=?
            """,
            (template_id,),
        ).fetchone()

    if not row:
        return api_error("Template not found")

    data = {
        "id": row["id"],
        "name": row["name"],
        "company": row["company"],
        "doc_type": row["doc_type"],
        "boxes": json.loads(row["boxes_json"]),
        "created_at": row["created_at"],
    }

    buf = BytesIO()
    buf.write(json.dumps(data, indent=2).encode("utf-8"))
    buf.seek(0)

    filename = f"template_{template_id}_{row['name'].replace(' ', '_')}.json"
    return send_file(
        buf,
        mimetype="application/json",
        as_attachment=True,
        download_name=filename,
    )


@redactor_bp.route("/template/import", methods=["POST"])
def template_import():
    """
    Import a template from a JSON file.
    """
    file = request.files.get("file")
    if not file:
        return api_error("No file uploaded")

    try:
        data = json.loads(file.read().decode("utf-8"))
    except Exception:
        return api_error("Invalid JSON file")

    name = data.get("name")
    company = data.get("company")
    doc_type = data.get("doc_type")
    boxes = data.get("boxes")

    if not name or not boxes:
        return api_error("Template name and boxes are required")

    boxes_json = json.dumps(boxes)
    ts = datetime.now().isoformat(timespec="seconds")

    with get_conn() as conn:
        ensure_templates_table(conn)
        ensure_template_versions_table(conn)

        cur = conn.execute(
            """
            INSERT INTO redaction_templates (name, company, doc_type, boxes_json, created_at)
            VALUES (?,?,?,?,?)
            """,
            (name, company, doc_type, boxes_json, ts),
        )
        template_id = cur.lastrowid

        conn.execute(
            """
            INSERT INTO redaction_template_versions
                (template_id, version, name, company, doc_type, boxes_json, created_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (template_id, 1, name, company, doc_type, boxes_json, ts),
        )

        conn.commit()

    return api_ok(message="Template imported", template_id=template_id)


# ------------------------------------------------------------
# REDACTION TEMPLATES — DUPLICATE / RENAME
# ------------------------------------------------------------
@redactor_bp.route("/template/duplicate", methods=["POST"])
def template_duplicate():
    """
    Duplicate an existing template under a new name.
    JSON body:
      {
        "template_id": 1,
        "new_name": "Copy of ..."
      }
    """
    data = request.json or {}
    template_id = data.get("template_id")
    new_name = data.get("new_name")

    if not template_id or not new_name:
        return api_error("template_id and new_name required")

    with get_conn() as conn:
        ensure_templates_table(conn)
        ensure_template_versions_table(conn)

        row = conn.execute(
            """
            SELECT name, company, doc_type, boxes_json
            FROM redaction_templates
            WHERE id=?
            """,
            (template_id,),
        ).fetchone()

        if not row:
            return api_error("Template not found")

        ts = datetime.now().isoformat(timespec="seconds")

        cur = conn.execute(
            """
            INSERT INTO redaction_templates (name, company, doc_type, boxes_json, created_at)
            VALUES (?,?,?,?,?)
            """,
            (new_name, row["company"], row["doc_type"], row["boxes_json"], ts),
        )
        new_id = cur.lastrowid

        conn.execute(
            """
            INSERT INTO redaction_template_versions
                (template_id, version, name, company, doc_type, boxes_json, created_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (new_id, 1, new_name, row["company"], row["doc_type"], row["boxes_json"], ts),
        )

        conn.commit()

    return api_ok(message="Template duplicated", template_id=new_id)


@redactor_bp.route("/template/rename", methods=["POST"])
def template_rename():
    """
    Rename an existing template.
    JSON body:
      {
        "template_id": 1,
        "new_name": "New Name"
      }
    """
    data = request.json or {}
    template_id = data.get("template_id")
    new_name = data.get("new_name")

    if not template_id or not new_name:
        return api_error("template_id and new_name required")

    with get_conn() as conn:
        ensure_templates_table(conn)
        conn.execute(
            "UPDATE redaction_templates SET name=? WHERE id=?",
            (new_name, template_id),
        )
        conn.commit()

    return api_ok(message="Template renamed")
