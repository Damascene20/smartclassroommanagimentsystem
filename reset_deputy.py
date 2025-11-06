# reset_deputy.py
import sqlite3

DB_FILE = "smart_classroom.db"

def connect_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except sqlite3.Error as e:
        print(f"[ERROR] Cannot connect to DB: {e}")
        return None

def reset_default_deputy(username="deputy", password="Deputy@123", name="Deputy of Studies"):
    conn = connect_db()
    if not conn:
        return

    cursor = conn.cursor()
    try:
        # Delete old deputy if exists
        cursor.execute("DELETE FROM Teachers WHERE Username = ?", (username,))
        conn.commit()
        print(f"[INFO] Old deputy '{username}' removed (if existed). ✅")

        # Insert new deputy with plain-text password
        cursor.execute("""
            INSERT INTO Teachers (Name, Username, Password, Role, IsApproved)
            VALUES (?, ?, ?, 'Deputy', 1)
        """, (name, username, password))
        conn.commit()
        print(f"[SUCCESS] Default deputy created: username='{username}', password='{password}' ✅")
    except sqlite3.Error as e:
        print(f"[ERROR] Failed to reset deputy: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    reset_default_deputy()
