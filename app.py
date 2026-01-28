import sys, os
# sys.stderr = open(os.devnull, "w")   # Silence ALL GIO warnings (disabled so we can see errors)

# Suppress GIO debug messages (optional, harmless)
os.environ["G_MESSAGES_DEBUG"] = ""

from app import create_app
from app.database import init_db

app = create_app()

# ------------------------------------------------------------
# SECRET KEY (required for flash messages, sessions, logins)
# ------------------------------------------------------------
app.secret_key = "rasesh_super_secret_key_2025"   # You can change this anytime

if __name__ == "__main__":

    # Initialize DB inside app context
    with app.app_context():
        init_db()

    print("=" * 60)
    print("🚀 Rasesh IM PDF CRM Generator")
    print("=" * 60)
    print("📊 Starting server...")
    print("📁 Uploads:   uploads/")
    print("📁 Output:    output/")
    print("📁 Database:  database.db")
    print("=" * 60)

    app.run(debug=True, host="0.0.0.0", port=5000)
