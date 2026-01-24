import os
from flask import Flask, render_template, request, jsonify
from settings import settings, save_settings

def create_app():
    app = Flask(__name__)

    # -----------------------------
    # ROOT / HOME – simple landing
    # -----------------------------
    @app.route("/")
    def home():
        return """
        <html>
          <head><title>Rasesh IM PDF CRM</title></head>
          <body style="font-family:Segoe UI, sans-serif; padding:20px;">
            <h1>Rasesh IM PDF CRM – Backend Running</h1>
            <p>Your server is live at <code>http://localhost:5000</code>.</p>
            <ul>
              <li><a href="/invoice/create">Create Invoice</a></li>
              <li><a href="/manifest/">Manifest Registry</a></li>
              <li><a href="/contacts/">Contacts</a></li>
              <li><a href="/vendor/">Vendors</a></li>
              <li><a href="/gst/">GST Numbers</a></li>
              <li><a href="/settings">Settings</a></li>
            </ul>
            <p>We’ll wire the redactor upload/viewer UI next.</p>
          </body>
        </html>
        """

    # -----------------------------
    # SETTINGS BLUEPRINT
    # -----------------------------
    from flask import Blueprint
    settings_bp = Blueprint("settings_bp", __name__)

    @settings_bp.route("/settings")
    def settings_page():
        return render_template("settings.html", settings=settings)

    @settings_bp.route("/settings/data")
    def settings_data():
        return jsonify(settings)

    @settings_bp.route("/settings/save", methods=["POST"])
    def settings_save():
        data = request.json
        settings.update(data)
        save_settings(settings)
        return jsonify({"success": True})

    app.register_blueprint(settings_bp)

    # -----------------------------
    # REGISTER OTHER BLUEPRINTS
    # -----------------------------
    from .redactor import redactor_bp
    from .invoice import invoice_bp
    from .manifest import manifest_bp
    from .contacts import contacts_bp
    from .vendor import vendor_bp
    from .gst import gst_bp

    app.register_blueprint(redactor_bp)
    app.register_blueprint(invoice_bp)
    app.register_blueprint(manifest_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(vendor_bp)
    app.register_blueprint(gst_bp)

    return app
