from flask import Blueprint, render_template, request, redirect, url_for, current_app
import sqlite3

gst_bp = Blueprint("gst", __name__, url_prefix="/gst")


def get_conn():
    """Return a SQLite connection using the app's configured DB path."""
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ------------------------------------------------------------
# GST LIST (now includes is_default)
# ------------------------------------------------------------
@gst_bp.route("/")
def gst_list():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, gst_number, is_default FROM gst ORDER BY gst_number"
        ).fetchall()

    return render_template("gst/list.html", gst=rows)


# ------------------------------------------------------------
# ADD GST (GET + POST)
# ------------------------------------------------------------
@gst_bp.route("/add", methods=["GET", "POST"])
def gst_add():
    if request.method == "POST":
        gst = request.form["gst"].strip()
        set_default = request.form.get("is_default") == "on"

        if gst:
            with get_conn() as conn:
                cur = conn.cursor()

                # Insert GST
                cur.execute(
                    "INSERT OR IGNORE INTO gst(gst_number) VALUES(?)",
                    (gst,)
                )

                # If user selected "Set as default"
                if set_default:
                    # Clear previous default
                    cur.execute("UPDATE gst SET is_default = 0")
                    # Set new default
                    cur.execute(
                        "UPDATE gst SET is_default = 1 WHERE gst_number = ?",
                        (gst,)
                    )

                conn.commit()

        return redirect(url_for("gst.gst_list"))

    # GET → show form
    return render_template("gst/form.html")


# ------------------------------------------------------------
# SET DEFAULT GST
# ------------------------------------------------------------
@gst_bp.route("/set_default/<int:id>")
def gst_set_default(id):
    with get_conn() as conn:
        cur = conn.cursor()

        # Clear all defaults
        cur.execute("UPDATE gst SET is_default = 0")

        # Set selected GST as default
        cur.execute(
            "UPDATE gst SET is_default = 1 WHERE id = ?",
            (id,)
        )

        conn.commit()

    return redirect(url_for("gst.gst_list"))


# ------------------------------------------------------------
# DELETE GST
# ------------------------------------------------------------
@gst_bp.route("/delete/<int:id>")
def gst_delete(id):
    with get_conn() as conn:
        conn.execute("DELETE FROM gst WHERE id=?", (id,))
        conn.commit()

    return redirect(url_for("gst.gst_list"))
