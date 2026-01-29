import os
import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash

signature_bp = Blueprint("signature", __name__, url_prefix="/signature")


def get_conn():
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------
# LIST
# ---------------------------------------------------------
@signature_bp.route("/list")
def signature_list():
    with get_conn() as conn:
        signatures = conn.execute(
            "SELECT id, name, position, filename, is_default FROM signatures ORDER BY id"
        ).fetchall()
    return render_template("signature/list.html", signatures=signatures)


# ---------------------------------------------------------
# ADD
# ---------------------------------------------------------
@signature_bp.route("/add", methods=["GET", "POST"])
def signature_add():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        position = (request.form.get("position") or "").strip()
        is_default = 1 if request.form.get("is_default") == "on" else 0
        file = request.files.get("file")

        if not name or not file or file.filename == "":
            flash("Name and image file are required.", "danger")
            return redirect(url_for("signature.signature_add"))

        # Ensure signatures folder exists
        base_dir = current_app.config["BASE_DIR"]
        sig_dir = os.path.join(base_dir, "static", "signatures")
        os.makedirs(sig_dir, exist_ok=True)

        # Save file
        filename = file.filename
        save_path = os.path.join(sig_dir, filename)
        file.save(save_path)

        with get_conn() as conn:
            cur = conn.cursor()

            if is_default:
                cur.execute("UPDATE signatures SET is_default=0")

            cur.execute(
                """
                INSERT INTO signatures(name, position, filename, is_default)
                VALUES (?, ?, ?, ?)
                """,
                (name, position, filename, is_default)
            )
            conn.commit()

        return redirect(url_for("signature.signature_list"))

    return render_template("signature/form.html")


# ---------------------------------------------------------
# EDIT
# ---------------------------------------------------------
@signature_bp.route("/edit/<int:signature_id>", methods=["GET", "POST"])
def signature_edit(signature_id):
    with get_conn() as conn:
        sig = conn.execute(
            "SELECT * FROM signatures WHERE id = ?", (signature_id,)
        ).fetchone()

    if not sig:
        flash("Signature not found.", "danger")
        return redirect(url_for("signature.signature_list"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        position = request.form.get("position", "").strip()
        is_default = 1 if request.form.get("is_default") == "on" else 0
        file = request.files.get("file")

        filename = sig["filename"]

        # If new file uploaded, replace old one
        if file and file.filename:
            base_dir = current_app.config["BASE_DIR"]
            sig_dir = os.path.join(base_dir, "static", "signatures")
            os.makedirs(sig_dir, exist_ok=True)

            filename = file.filename
            file.save(os.path.join(sig_dir, filename))

        with get_conn() as conn:
            cur = conn.cursor()

            if is_default:
                cur.execute("UPDATE signatures SET is_default=0")

            cur.execute(
                """
                UPDATE signatures
                SET name=?, position=?, filename=?, is_default=?
                WHERE id=?
                """,
                (name, position, filename, is_default, signature_id)
            )
            conn.commit()

        return redirect(url_for("signature.signature_list"))

    return render_template("signature/form.html", signature=sig)


# ---------------------------------------------------------
# DELETE
# ---------------------------------------------------------
@signature_bp.route("/delete/<int:signature_id>", methods=["POST"])
def signature_delete(signature_id):
    with get_conn() as conn:
        sig = conn.execute(
            "SELECT filename FROM signatures WHERE id = ?", (signature_id,)
        ).fetchone()

        if sig:
            # Delete file from disk
            base_dir = current_app.config["BASE_DIR"]
            file_path = os.path.join(base_dir, "static", "signatures", sig["filename"])
            if os.path.exists(file_path):
                os.remove(file_path)

            # Delete DB row
            conn.execute("DELETE FROM signatures WHERE id = ?", (signature_id,))
            conn.commit()

    flash("Signature deleted.", "success")
    return redirect(url_for("signature.signature_list"))
