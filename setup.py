from werkzeug.security import generate_password_hash
import json
import os

DATA_FILE = "course_data.json"

def create_default_user():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                data = json.load(f)
                if data.get("users"):
                    print("Users already exist. No changes made.")
                    return
            except:
                pass

    data = {
        "users": [
            {
                "id": 1,
                "username": "admin",
                "password": generate_password_hash("admin123"),
                "name": "Administrator",
                "role": "teacher",
                "created_at": "2026-06-11 00:00:00"
            }
        ],
        "courses": []
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("   Default admin account created!")
    print("   Username: admin")
    print("   Password: admin123")
    print("   Please change the password after first login.")

if __name__ == "__main__":
    create_default_user()