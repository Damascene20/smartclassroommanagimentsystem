# ✅ db_setup.py — FINAL UPDATED VERSION
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash  # Secure password hashing

DB_FILE = "smart_classroom.db"


# -------------------- DATABASE CONNECTION --------------------
def connect_db():
    """Connects to the SQLite database and returns the connection object."""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = None  # or sqlite3.Row for dict-like access
        return conn
    except sqlite3.Error as e:
        print(f"[ERROR] Database connection failed: {e}")
        return None


# -------------------- INITIALIZATION --------------------
def initialize_database():
    """
    Creates or updates all required tables.
    Automatically adds missing columns (like ApprovedDate, UploadDate) and ensures default data.
    """
    conn = connect_db()
    if not conn:
        print("[FATAL] Cannot initialize database — connection failed.")
        return

    cursor = conn.cursor()
    try:
        # ----------- TEACHERS -----------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Teachers (
                TeacherID INTEGER PRIMARY KEY AUTOINCREMENT,
                Name TEXT NOT NULL,
                Subject TEXT,
                Username TEXT UNIQUE NOT NULL,
                Password TEXT NOT NULL,
                Role TEXT DEFAULT 'Teacher',
                IsApproved INTEGER DEFAULT 0,
                Email TEXT,
                Phone TEXT,
                Class TEXT
            )
        """)

        # ----------- CLASSROOMS -----------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Classrooms (
                RoomID INTEGER PRIMARY KEY AUTOINCREMENT,
                Name TEXT UNIQUE NOT NULL,
                EquipmentList TEXT
            )
        """)
        default_rooms = [
            ('SMART Lab 1', 'Interactive Whiteboard, Projector, 30 PCs'),
            ('SMART Lab 2', 'Projector, 25 Laptops'),
            ('Meeting Room A', 'Interactive Display, Video Conferencing Equipment')
        ]
        for name, equipment in default_rooms:
            cursor.execute("INSERT OR IGNORE INTO Classrooms (Name, EquipmentList) VALUES (?, ?)", (name, equipment))

        # ----------- BOOKINGS -----------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Bookings (
                BookingID INTEGER PRIMARY KEY AUTOINCREMENT,
                TeacherID INTEGER NOT NULL,
                RoomID INTEGER NOT NULL,
                Date TEXT NOT NULL,
                StartTime TEXT NOT NULL,
                EndTime TEXT NOT NULL,
                Equipment TEXT,
                Status TEXT DEFAULT 'Pending',
                FOREIGN KEY (TeacherID) REFERENCES Teachers(TeacherID),
                FOREIGN KEY (RoomID) REFERENCES Classrooms(RoomID)
            )
        """)

        # ----------- SYSTEM SETTINGS -----------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS SystemSettings (
                Key TEXT PRIMARY KEY,
                Value TEXT NOT NULL
            )
        """)
        settings = [
            ('session_duration', '40'),
            ('lab_status', 'Available'),
            ('booking_cutoff_minutes', '40'),
        ]
        for key, val in settings:
            cursor.execute("INSERT OR IGNORE INTO SystemSettings (Key, Value) VALUES (?, ?)", (key, val))

        # ----------- MATERIAL REQUESTS -----------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS MaterialRequests (
                RequestID INTEGER PRIMARY KEY AUTOINCREMENT,
                FullName TEXT NOT NULL,
                Gender TEXT NOT NULL,
                PhoneNumber TEXT NOT NULL,
                ClassTeacher TEXT,
                MaterialName TEXT NOT NULL,
                BorrowedDate TEXT NOT NULL,
                ReturnedDate TEXT NOT NULL,
                Reason TEXT,
                LetterFile TEXT NOT NULL,
                Status TEXT DEFAULT 'Pending',
                ApprovedDate TEXT,
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ✅ Ensure ApprovedDate exists
        cursor.execute("PRAGMA table_info(MaterialRequests)")
        mat_columns = [col[1] for col in cursor.fetchall()]
        if "ApprovedDate" not in mat_columns:
            cursor.execute("ALTER TABLE MaterialRequests ADD COLUMN ApprovedDate TEXT")
            print("[INFO] Added missing column: ApprovedDate ✅")

        # ----------- TEACHER DOCUMENTS -----------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS TeacherDocuments (
                DocumentID INTEGER PRIMARY KEY AUTOINCREMENT,
                TeacherID INTEGER NOT NULL,
                FileName TEXT NOT NULL,
                FilePath TEXT NOT NULL,
                UploadDate TEXT,
                FOREIGN KEY (TeacherID) REFERENCES Teachers(TeacherID)
            )
        """)

        # ✅ Ensure UploadDate exists (migration-safe)
        cursor.execute("PRAGMA table_info(TeacherDocuments)")
        doc_columns = [col[1] for col in cursor.fetchall()]
        if "UploadDate" not in doc_columns:
            cursor.execute("ALTER TABLE TeacherDocuments ADD COLUMN UploadDate TEXT")
            print("[INFO] Added missing column: UploadDate ✅")

        conn.commit()
        print("[SUCCESS] Database initialized and all tables verified. ✅")

    except sqlite3.Error as e:
        print(f"[ERROR] Database setup failed: {e}")
    finally:
        conn.close()


# -------------------- MIGRATION HELPERS --------------------
def migrate_teacher_roles():
    """Ensures all teachers have a valid Role (default = 'Teacher')."""
    conn = connect_db()
    if not conn:
        print("[ERROR] Cannot migrate teacher roles — DB connection failed.")
        return

    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE Teachers
            SET Role = 'Teacher'
            WHERE Role IS NULL OR Role = ''
        """)
        conn.commit()
        print("[INFO] Teacher roles migration completed. ✅")
    except sqlite3.Error as e:
        print(f"[ERROR] Failed to migrate teacher roles: {e}")
    finally:
        conn.close()


# -------------------- DEFAULT DEPUTY --------------------
def create_default_deputy(username="deputy", password="Deputy@123", name="Deputy of Studies"):
    """Creates a default Deputy account if it doesn't exist."""
    conn = connect_db()
    if not conn:
        print("[ERROR] DB connection failed.")
        return False

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT TeacherID FROM Teachers WHERE Username = ?", (username,))
        if cursor.fetchone():
            print(f"[INFO] Default deputy '{username}' already exists. ✅")
            return True

        hashed_password = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO Teachers (Name, Username, Password, Role, IsApproved)
            VALUES (?, ?, ?, 'Deputy', 1)
        """, (name, username, hashed_password))
        conn.commit()
        print(f"[SUCCESS] Default deputy created: username='{username}', password='{password}' (change after first login). ✅")
        return True
    except sqlite3.Error as e:
        print(f"[ERROR] Failed to create default deputy: {e}")
        return False
    finally:
        conn.close()


# -------------------- MANUAL DEPUTY REGISTRATION --------------------
def register_deputy(name, username, password):
    """ICT_Admin can manually register Deputy accounts (password hashed)."""
    conn = connect_db()
    if not conn:
        return "[ERROR] DB connection failed."

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT TeacherID FROM Teachers WHERE Username = ?", (username,))
        if cursor.fetchone():
            return "Username already exists."

        hashed_password = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO Teachers (Name, Username, Password, Role, IsApproved)
            VALUES (?, ?, ?, 'Deputy', 1)
        """, (name, username, hashed_password))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"[ERROR] Could not register deputy: {e}")
        return False
    finally:
        conn.close()


# -------------------- MAIN EXECUTION --------------------
if __name__ == "__main__":
    
    initialize_database()
    migrate_teacher_roles()
    create_default_deputy(username="deputy", password="Deputy@123", name="Deputy of Studies")
