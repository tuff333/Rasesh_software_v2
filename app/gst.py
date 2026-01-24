from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3
from .database import DB_PATH

gst_bp = Blueprint("gst", __name__, url_prefix="/gst")

@gst_bp.route("/")
def gst_list():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id, gst FROM gst_numbers ORDER BY gst").fetchall()
    conn.close()
    return render_template("gst/list.html", gst=rows)

@gst_bp.route("/add", methods=["POST"])
def gst_add():
    gst = request.form["gst"].strip()
    if not gst:
        return redirect(url_for("gst.gst_list"))

    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR IGNORE INTO gst_numbers(gst) VALUES(?)", (gst,))
    conn.commit()
    conn.close()
    return redirect(url_for("gst.gst_list"))

@gst_bp.route("/delete/<int:id>")
def gst_delete(id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM gst_numbers WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("gst.gst_list"))
