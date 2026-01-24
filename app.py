from app import create_app
from app.database import init_db
from settings import settings, save_settings, load_settings

app = create_app()

if __name__ == "__main__":
    init_db()

    print("=" * 60)
    print("🚀 Rasesh IM PDF CRM Generator")
    print("=" * 60)
    print("📊 Dashboard: http://localhost:5000")
    print("📁 Uploads:   uploads/")
    print("📁 Output:    output/")
    print("📁 Database:  database.db")
    print("=" * 60)

    app.run(debug=True, host="0.0.0.0", port=5000)
