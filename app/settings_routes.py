from flask import Blueprint, render_template

settings_page_bp = Blueprint("settings_page_bp", __name__)

@settings_page_bp.route("/settings")
def settings_page():
    return render_template("settings.html")
