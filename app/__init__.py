import os
from flask import Flask, render_template


def create_app():
    # Root-level templates and static folders
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    template_dir = os.path.join(base_dir, "templates")
    static_dir = os.path.join(base_dir, "static")

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    # ------------------------------------------------------------
    # Global config
    # ------------------------------------------------------------
    app.config["BASE_DIR"] = base_dir
    app.config["UPLOAD_FOLDER"] = os.path.join(base_dir, "uploads")
    app.config["OUTPUT_FOLDER"] = os.path.join(base_dir, "output")
    app.config["DATABASE"] = os.path.join(base_dir, "database.db")

    # ------------------------------------------------------------
    # Ensure required folders exist
    # ------------------------------------------------------------
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["OUTPUT_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.config["OUTPUT_FOLDER"], "temp"), exist_ok=True)
    os.makedirs(os.path.join(app.config["OUTPUT_FOLDER"], "redactions"), exist_ok=True)
    os.makedirs(os.path.join(app.config["OUTPUT_FOLDER"], "invoices"), exist_ok=True)
    os.makedirs(os.path.join(app.config["OUTPUT_FOLDER"], "manifests"), exist_ok=True)

    # ------------------------------------------------------------
    # Initialize database INSIDE app context
    # ------------------------------------------------------------
    from .database import init_db
    with app.app_context():
        init_db()

    # ------------------------------------------------------------
    # Import blueprints
    # ------------------------------------------------------------
    from .invoice import invoice_bp
    from .manifest import manifest_bp
    from .contacts import contacts_bp
    from .vendor import vendor_bp
    from .gst import gst_bp
    from .redactor import redactor_bp
    from .services.settings import settings_bp
    from app.invoice_routes import invoice_routes_bp
    from app.invoice_items import invoice_items_bp
    from app.signature import signature_bp

    # ------------------------------------------------------------
    # Register blueprints
    # ------------------------------------------------------------
    app.register_blueprint(invoice_bp)
    app.register_blueprint(invoice_routes_bp)
    app.register_blueprint(manifest_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(vendor_bp)
    app.register_blueprint(gst_bp)
    app.register_blueprint(redactor_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(invoice_items_bp)
    app.register_blueprint(signature_bp)

    # ------------------------------------------------------------
    # Dashboard page
    # ------------------------------------------------------------
    @app.route("/")
    def dashboard():
        from .dashboard import get_dashboard_stats
        stats = get_dashboard_stats()
        return render_template("dashboard.html", **stats)
    
    @app.route("/settings")
    def settings_page():
        return render_template("settings.html")


    return app
