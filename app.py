# app.py - FINAL CORRECTED VERSION

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import sqlite3
from werkzeug.utils import secure_filename
import sqlite3
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer

from flask import make_response
from datetime import date
import functools
from db_setup import connect_db, initialize_database
import csv
from datetime import datetime # <-- Import the datetime object
from collections import defaultdict
from collections import Counter
import os
from smart_scheduler import submit_teacher_document
from smart_scheduler import get_all_classrooms, get_all_teachers, get_all_bookings
from math import ceil
# Note: Removed unused imports: datetime, timedelta, Counter, defaultdict, etc.

from werkzeug.security import generate_password_hash
# Import DB and Core Logic
# Assuming db_setup.py and smart_scheduler.py are in place and correct
from db_setup import connect_db, initialize_database, register_deputy
from smart_scheduler import (
    run_database_migrations,  
    get_teacher_by_id, get_teacher_by_username, register_ict_admin, 
    get_system_setting, 
    update_system_setting, get_all_rooms, get_available_hours,
    submit_booking_request, update_booking_status, calculate_end_time, 
    get_bookings_by_teacher_id, get_pending_requests,
    get_all_teacher_management_data, update_teacher_approval_status, 
    delete_teacher_by_id, get_usage_reports_and_summary,
    get_all_bookings # Added missing import
)
from flask import Flask
from itsdangerous import URLSafeTimedSerializer
# --- Flask App Setup ---
app = Flask(__name__)

app.config['SECRET_KEY'] = 'your_very_secret_key_here'

# Flask-Mail settings (example with Gmail)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'nshimiryayodamas@gmail.com'
app.config['MAIL_PASSWORD'] = 'fnlo ttfa qhww gdlw'
MAIL_DEFAULT_SENDER='nshimiryayodamas@gmail.com'
from flask_mail import Mail
mail = Mail(app)
# *** IMPORTANT: Change this to a secure, long random string for production ***
app.secret_key = 'your_super_secure_secret_key_12345' 
DB_FILE = "smart_classroom.db"
UPLOAD_FOLDER = "uploads/letters"
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
DB_FILE = "smart_classroom.db" # Required for get_db_connection
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
s = URLSafeTimedSerializer(app.secret_key)
serializer = URLSafeTimedSerializer(app.secret_key)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Define get_db_connection locally or import if not defined elsewhere for utilities
def get_db_connection():
    """Returns a SQLite connection with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn
def send_reset_email(user_email):
    token = generate_reset_token(user_email)
    reset_url = f'http://127.0.0.1:5000/reset_password/{token}'
    
    msg = Message("Smart Classroom Password Reset",
                  sender="no-reply@smartclassroom.com",
                  recipients=[user_email])
    msg.body = f"Hello,\n\nClick the link below to reset your password:\n{reset_url}\n\nThis link is valid for 1 hour."
    mail.send(msg)
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            # Generate secure token
            token = serializer.dumps(email, salt="password-reset-salt")
            
            # Use your online app domain (Render)
            reset_url = f"https://smartclassroommanagamentsystem.onrender.com/reset_password/{token}"

            # Send email
            msg = Message(
                subject="Password Reset Request",
                sender="noreply@smartclassroom.com",
                recipients=[email],
                body=f"Click the link below to reset your password:\n\n{reset_url}\n\nIf you didn’t request this, ignore this email."
            )
            mail.send(msg)

            flash("✅ A password reset link has been sent to your email.", "success")
            return redirect(url_for("login"))
        else:
            flash("❌ Email not found. Please try again.", "danger")

    return render_template("forgot_password.html")

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        # Verify token (expires in 30 minutes)
        email = serializer.loads(token, salt='password-reset-salt', max_age=1800)
    except Exception:
        flash("❌ The reset link is invalid or has expired.", "danger")
        return redirect(url_for('send_reset_link'))

    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("❌ Passwords do not match.", "danger")
            return redirect(request.url)

        try:
            hashed_password = generate_password_hash(password)
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE Users SET Password=? WHERE Email=?", (hashed_password, email))
            conn.commit()
            conn.close()
            flash("✅ Password reset successfully! You can now login.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Error updating password: {e}", "danger")

    return render_template('reset_password.html')

 
# --- Session-Based User Utility ---
def generate_reset_token(email):
    # Create serializer directly
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt="password-reset-salt")

def verify_reset_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        # Returns the email if token is valid and not expired
        email = serializer.loads(token, salt="password-reset-salt", max_age=expiration)
        return email
    except Exception:
        # Token invalid or expired
        return None
@app.route('/send_reset_link', methods=['GET', 'POST'])
def send_reset_link():
    if request.method == 'POST':
        email = request.form['email']
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Users WHERE Email=?", (email,))
            user = cursor.fetchone()
            conn.close()

            if not user:
                flash("❌ Email not registered.", "danger")
                return redirect(url_for('send_reset_link'))

            # Generate token
            token = serializer.dumps(email, salt='password-reset-salt')
            reset_link = url_for('reset_password', token=token, _external=True)

            # Send email
            msg = Message("Smart Classroom - Reset Your Password",
                          sender=app.config['MAIL_USERNAME'], recipients=[email])
            msg.body = f"Click the link to reset your password:\n\n{reset_link}\n\nThis link is valid for 30 minutes."
            mail.send(msg)

            flash("✅ Reset link sent to your email.", "success")
        except Exception as e:
            flash(f"Error sending email: {e}", "danger")

    return render_template('send_reset_link.html')


def confirm_reset_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=expiration)
    except Exception:
        return None
    return email
def get_current_user():
    """Retrieves the user data from the database based on the session ID."""
    user_id = session.get('user_id')
    if user_id:
        user_data = get_teacher_by_id(user_id)
        if user_data:
            # Map the tuple to a dictionary for easy access (based on smart_scheduler structure)
            keys = ["id", "name", "subject", "username", "password", "role", "is_approved", "email", "phone", "class"]
            user = dict(zip(keys, user_data))
            return user
    return None

# ----------------------------
# Decorators for authentication (Still defined, but unused below)
# ----------------------------

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        current_user = get_current_user()
        if not current_user or current_user.get('role') != 'ICT_Admin':
            flash('Access denied. ICT Admin privileges required.', 'danger')
            # Redirect admin failures to the main teacher booking page
            return redirect(url_for('bookings')) 
        return view(**kwargs)
    return wrapped_view

# ----------------------------
# App Initialization Logic
# ----------------------------

def create_default_user():
    """Ensures database is initialized, migrations run, and default admin exists."""
    initialize_database() 
    run_database_migrations() 

    # Default admin credentials
    username = "admin"
    password = "admin123" 
    name = "System Administrator"
    
    if not get_teacher_by_username(username):
        success = register_ict_admin(name, username, password)
        if success:
            print(f"INFO: Default '{username}' user created.")

# Run initialization on startup
create_default_user()

# ----------------------------
# Routes: Authentication
# ----------------------------
@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        # Fetch user by username
        user_data = get_teacher_by_username(username)  
        # user_data = (TeacherID, Name, Subject, Username, Password, Role, IsApproved, ...)

        if user_data:
            stored_password = user_data[4]  # Password from DB (plain text)
            if password == stored_password:  # Direct comparison
                teacher_id, name, role, is_approved = user_data[0], user_data[1], user_data[5], user_data[6]

                # Store session data
                session['user_id'] = teacher_id
                session['username'] = name
                session['role'] = role

                flash(f'Welcome, {name}!', 'success')

                # Redirect based on role
                if role == 'ICT_Admin':
                    return redirect(url_for('ict_admin_dashboard'))
                elif role == 'Deputy':
                    return redirect(url_for('deputy_dashboard'))
                elif role == 'Teacher':
                    if is_approved == 0:
                        flash('Your account is pending ICT Teacher approval.', 'warning')
                        return redirect(url_for('user_status'))
                    else:
                        return redirect(url_for('bookings'))
                else:
                    flash('Unknown role. Contact system administrator.', 'danger')
                    return redirect(url_for('login'))
            else:
                flash('Invalid username or password.', 'danger')
        else:
            flash('Invalid username or password.', 'danger')

    # System settings for display on login page
    duration = get_system_setting('session_duration') or 40
    lab_status = get_system_setting('lab_status') or 'Available'

    return render_template('login.html', session_duration=duration, lab_status=lab_status)



@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # --- Existing fields ---
        name = request.form['name']
        subject = request.form['subject']
        username = request.form['username']
        password = request.form['password'] # NOTE: You should hash this password!

        # --- NEW fields retrieved from the form ---
        email = request.form['email']
        phone = request.form['phone']
        gender = request.form['gender']
        # Use .get() for optional fields like Class Teacher
        class_teacher = request.form.get('class_teacher', '') 

        # 1. Check if username or email already exists
        if get_teacher_by_username(username):
            flash('Username already exists. Please choose another.', 'danger')
            return render_template('register.html')
            
        # Optional: Check if email already exists
        # if get_teacher_by_email(email): 
        #     flash('Email already registered.', 'danger')
        #     return render_template('register.html')

        # 2. Database Insertion
        conn = connect_db()
        cursor = conn.cursor()
        
        # 3. Update the SQL query to include the new columns and values
        cursor.execute("""
            INSERT INTO Teachers 
                (Name, Subject, Username, Password, Email, Phone, Gender, ClassTeacher, Role, IsApproved)
            VALUES 
                (?, ?, ?, ?, ?, ?, ?, ?, 'Teacher', 0)
        """, (name, subject, username, password, email, phone, gender, class_teacher))
        
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please wait for ICT Teacher approval.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/status')
def user_status():
    teacher_info = get_current_user()
    if teacher_info:
        is_approved = teacher_info.get('is_approved')
        name = teacher_info.get('name') 
        
        status_text = "Approved! You can now access booking pages." if is_approved == 1 else "Pending approval by the ICT Teacher."
        status_class = "success" if is_approved == 1 else "warning"
        return render_template('user_status.html', name=name, status=status_text, status_class=status_class)
    return redirect(url_for('logout'))

# ----------------------------
# Routes: Teacher Booking
# ----------------------------


@app.route("/teacher/bookings")
def teacher_bookings():
    teacher_id = session.get('user_id') 
    if not teacher_id:
        return redirect(url_for('logout'))

    # NOTE: Replaced current_user.id with session-based ID
    bookings = get_bookings_by_teacher_id(teacher_id) 
    return render_template("teacher_bookings.html", bookings=bookings)

# ----------------------------
# Routes: Admin Interface
# ----------------------------

@app.route('/ict_admin/dashboard')
def ict_admin_dashboard():
    pending_requests = get_pending_requests()
    return render_template('ict_admin_dashboard.html', pending_requests=pending_requests)

@app.route('/admin/manage_teachers')
def manage_teachers():
    # Pagination settings
    page = request.args.get('page', 1, type=int)  # Current page
    per_page = 5  # Display 5 teachers per page

    # Fetch all teachers
    all_teachers = get_all_teacher_management_data()
    total = len(all_teachers)

    # Slice for current page
    start = (page - 1) * per_page
    end = start + per_page
    teachers_data = all_teachers[start:end]

    # Pagination flags
    total_pages = (total + per_page - 1) // per_page  # ceil division

    return render_template(
        "manage_teachers.html",
        teachers=teachers_data,
        total_teachers=total,
        page=page,
        total_pages=total_pages
    )


# 2. Approve or deny teacher
@app.route('/admin/manage_teachers/<int:teacher_id>/<action>', methods=['POST'])
def approve_teacher_account(teacher_id, action):
    if action not in ['approve', 'deny']:
        flash("Invalid action", "danger")
        return redirect(url_for('manage_teachers'))
    
    status = 1 if action == 'approve' else 0 
    
    if update_teacher_approval_status(teacher_id, status):
        flash(f"Teacher has been {'approved' if status==1 else 'denied'} successfully!", "success")
    else:
        flash(f"Failed to update teacher status.", "danger")
        
    return redirect(url_for('manage_teachers'))

# 3. Edit Teacher Page (FIXED MISSING ROUTE)
@app.route('/admin/manage_teachers/edit/<int:teacher_id>', methods=['GET', 'POST'])
def edit_teacher_page(teacher_id):
    """Handles displaying and updating a teacher's details."""
    conn = connect_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if request.method == "POST":
        name = request.form.get("name")
        subject = request.form.get("subject")
        username = request.form.get("username")
        role = request.form.get("role")
        email = request.form.get("email")
        phone = request.form.get("phone")
        class_assigned = request.form.get("class")
        
        try:
            cursor.execute("""
                UPDATE Teachers
                SET Name=?, Subject=?, Username=?, Role=?, Email=?, Phone=?, Class=?
                WHERE TeacherID=?
            """, (name, subject, username, role, email, phone, class_assigned, teacher_id))
            conn.commit()
            flash(f"Teacher {name} information updated successfully!", "success")
        except sqlite3.Error as e:
            flash(f"Error updating teacher: {e}", "danger")
        finally:
            conn.close()
            return redirect(url_for('manage_teachers'))
    
    cursor.execute("SELECT * FROM Teachers WHERE TeacherID=?", (teacher_id,))
    teacher = cursor.fetchone()
    conn.close()
    
    if not teacher:
        flash("Teacher not found.", "danger")
        return redirect(url_for('manage_teachers'))
        
    return render_template("edit_teacher.html", teacher=teacher)


# 4. Delete teacher
@app.route('/admin/manage_teachers/delete/<int:teacher_id>', methods=['POST'])
def delete_teacher_account(teacher_id): 
    # NOTE: Renamed to avoid clash with imported function
    if delete_teacher_by_id(teacher_id):
        flash("Teacher and associated bookings deleted successfully!", "success")
    else:
        flash("Failed to delete teacher (ICT Admin accounts cannot be deleted).", "danger")
    return redirect(url_for('manage_teachers'))


@app.route("/admin/approve_booking/<int:booking_id>", methods=["GET", "POST"])
def approve_booking(booking_id):
    update_booking_status(booking_id, "Approved")
    flash("Booking approved!", "success")
    return redirect(url_for("manage_bookings"))

@app.route('/manage_bookings')
def manage_bookings():
    conn = connect_db()
    cursor = conn.cursor()

    # Pagination settings
    page = request.args.get('page', 1, type=int)  # Current page
    per_page = 5  # Show 5 bookings per page
    offset = (page - 1) * per_page

    # Fetch paginated bookings with teacher and room names
    cursor.execute("""
        SELECT 
            b.BookingID,
            t.Name AS TeacherName,
            c.Name AS RoomName,
            b.Date,
            b.StartTime,
            b.EndTime,
            b.Equipment,
            b.Status
        FROM Bookings b
        LEFT JOIN Teachers t ON b.TeacherID = t.TeacherID
        LEFT JOIN Classrooms c ON b.RoomID = c.RoomID
        ORDER BY b.Date DESC
        LIMIT ? OFFSET ?
    """, (per_page, offset))
    bookings = cursor.fetchall()

    # Get total number of bookings
    cursor.execute("SELECT COUNT(*) FROM Bookings")
    total = cursor.fetchone()[0]
    total_pages = (total + per_page - 1) // per_page  # ceil division

    # Ensure page is within bounds
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    conn.close()

    return render_template(
        'manage_bookings.html',
        bookings=bookings,
        page=page,
        total_pages=total_pages
    )

@app.route('/manage_teacherbook')
def manage_teacherbook():
    conn = connect_db()
    cursor = conn.cursor()

    # Pagination settings
    page = request.args.get('page', 1, type=int)  # Current page
    per_page = 5  # Show 5 bookings per page
    offset = (page - 1) * per_page

    # Fetch paginated bookings with teacher and room names
    cursor.execute("""
        SELECT 
            b.BookingID,
            t.Name AS TeacherName,
            c.Name AS RoomName,
            b.Date,
            b.StartTime,
            b.EndTime,
            b.Equipment,
            b.Status
        FROM Bookings b
        LEFT JOIN Teachers t ON b.TeacherID = t.TeacherID
        LEFT JOIN Classrooms c ON b.RoomID = c.RoomID
        ORDER BY b.Date DESC
        LIMIT ? OFFSET ?
    """, (per_page, offset))
    bookings = cursor.fetchall()

    # Get total number of bookings
    cursor.execute("SELECT COUNT(*) FROM Bookings")
    total = cursor.fetchone()[0]
    total_pages = (total + per_page - 1) // per_page  # ceil division

    # Ensure page is within bounds
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    conn.close()

    return render_template(
        'manage_teacherbook.html',
        bookings=bookings,
        page=page,
        total_pages=total_pages
    )



@app.route("/admin/deny_booking/<int:booking_id>", methods=["POST"])
def deny_booking(booking_id):
    update_booking_status(booking_id, "Denied")
    flash("Booking denied!", "warning")
    return redirect(url_for("manage_bookings"))

# ----------------------------
# Routes: Reports & Settings
# ----------------------------



# Dummy function to simulate fetching data for reports
def get_reports_data():
    """Fetches sales, users, and a general summary for the admin reports page."""
    
    # 1. Define the variables you want to pass to the template
    reports_data = [
        {"id": 1, "metric": "Total Users", "value": 1500},
        {"id": 2, "metric": "New Orders (Last 7 Days)", "value": 245},
        {"id": 3, "metric": "Total Revenue", "value": "$125,000"},
    ]
    
    # This is the variable that was causing the 'UndefinedError'
    summary = "System performance is optimal, with a 15% growth in new users this month."
    
    return reports_data, summary





@app.route('/admin/ict_admin_settings', methods=['GET', 'POST'])
def ict_admin_settings():
    if request.method == 'POST':
        new_duration = request.form.get('session_duration')
        new_status = request.form.get('lab_status')
        new_cutoff = request.form.get('booking_cutoff_minutes')
        
        if new_duration: update_system_setting('session_duration', new_duration)
        if new_status: update_system_setting('lab_status', new_status)
        if new_cutoff: update_system_setting('booking_cutoff_minutes', new_cutoff)
        
        flash("System settings updated!", "success")
        return redirect(url_for('ict_admin_settings'))

    # Retrieve current settings
    settings = {
        'session_duration': get_system_setting('session_duration') or '40',
        'lab_status': get_system_setting('lab_status') or 'Available',
        'booking_cutoff_minutes': get_system_setting('booking_cutoff_minutes') or '40'
    }

    return render_template("ict_admin_settings.html", settings=settings)



@app.context_processor
def inject_global_vars():
    """Globally injects the current datetime object for use in base.html footer."""
    return {'now': datetime.now()}

# --- SIMULATION FUNCTIONS (Replace with actual Database Queries) ---

def calculate_status_summary():
    """Fetches the count of bookings by Status from the database."""
    conn = connect_db()
    if not conn:
        return {'Approved': 0, 'Pending': 0, 'Denied': 0, 'Cancelled': 0}

    cursor = conn.cursor()
    # Query: SELECT Status, COUNT(BookingID) FROM Bookings GROUP BY Status
    cursor.execute("SELECT Status, COUNT(BookingID) AS Count FROM Bookings GROUP BY Status")
    results = cursor.fetchall()
    conn.close()
    
    status_summary = {row['Status']: row['Count'] for row in results}
    
    # Ensure all required keys exist (defaulting to 0)
    default_summary = {'Approved': 0, 'Pending': 0, 'Denied': 0, 'Cancelled': 0}
    default_summary.update(status_summary)
    
    return default_summary

def calculate_teacher_ranking():
    """Fetches and ranks teachers by number of Approved bookings."""
    conn = connect_db()
    if not conn:
        return []
        
    cursor = conn.cursor()
    # Query: JOIN Teachers and Bookings, filter by Approved, group by Teacher Name, order by count DESC
    cursor.execute("""
        SELECT 
            T.Name, 
            COUNT(B.BookingID) AS Count
        FROM Bookings B
        JOIN Teachers T ON B.TeacherID = T.TeacherID
        WHERE B.Status = 'Approved'
        GROUP BY T.Name
        ORDER BY Count DESC
        LIMIT 10
    """)
    # Results are (Name, Count)
    results = cursor.fetchall()
    conn.close()
    
    # Convert sqlite3.Row objects to list of tuples for the template
    return [(row['Name'], row['Count']) for row in results]

def calculate_subject_ranking():
    """Fetches and ranks subjects by number of Approved bookings."""
    conn = connect_db()
    if not conn:
        return []
        
    cursor = conn.cursor()
    # Note: Your Bookings table does not have a 'subject' column, 
    # but the Teachers table does. We'll use the Teacher's Subject.
    # If the booking itself specifies the subject, you must add it to the Bookings table.
    
    # Assuming we get the subject from the Teacher tied to the approved booking:
    cursor.execute("""
        SELECT 
            T.Subject, 
            COUNT(B.BookingID) AS Count
        FROM Bookings B
        JOIN Teachers T ON B.TeacherID = T.TeacherID
        WHERE B.Status = 'Approved' AND T.Subject IS NOT NULL
        GROUP BY T.Subject
        ORDER BY Count DESC
        LIMIT 10
    """)
    results = cursor.fetchall()
    conn.close()
    
    # Convert to list of tuples for the template
    return [(row['Subject'], row['Count']) for row in results]

# --- THE FLASK ENDPOINT ---


@app.route('/admin/reports')
def admin_reports():
    conn = connect_db()
    cursor = conn.cursor()

    # --- Booking summary ---
    cursor.execute("SELECT Status, COUNT(*) FROM Bookings GROUP BY Status")
    summary = {row[0]: row[1] for row in cursor.fetchall()}

    # --- Teacher ranking ---
    cursor.execute("""
        SELECT T.Name, COUNT(B.BookingID)
        FROM Bookings B
        JOIN Teachers T ON B.TeacherID = T.TeacherID
        WHERE B.Status = 'Approved'
        GROUP BY T.Name
        ORDER BY COUNT(B.BookingID) DESC
    """)
    teacher_ranking = cursor.fetchall()

    # --- Subject ranking ---
    cursor.execute("""
        SELECT T.Subject, COUNT(B.BookingID)
        FROM Bookings B
        JOIN Teachers T ON B.TeacherID = T.TeacherID
        WHERE B.Status = 'Approved'
        GROUP BY T.Subject
        ORDER BY COUNT(B.BookingID) DESC
    """)
    subject_ranking = cursor.fetchall()

    # --- Teacher list ---
    cursor.execute("""
        SELECT T.Name, T.Email, T.Phone, 
               COUNT(B.BookingID) AS Bookings
        FROM Teachers T
        LEFT JOIN Bookings B ON T.TeacherID = B.TeacherID
        GROUP BY T.TeacherID
    """)
    teacher_list = [
        dict(Name=row[0], Email=row[1], Phone=row[2], Bookings=row[3])
        for row in cursor.fetchall()
    ]

    conn.close()

    # --- Current date/time ---
    now = datetime.now()

    return render_template(
        'admin/reports.html',
        now=now,
        summary=summary,
        teacher_ranking=teacher_ranking,
        subject_ranking=subject_ranking,
        teacher_list=teacher_list
    )

@app.route('/admin/report')
def admin_report():
    conn = connect_db()
    cursor = conn.cursor()

    # --- Booking summary ---
    cursor.execute("SELECT Status, COUNT(*) FROM Bookings GROUP BY Status")
    summary = {row[0]: row[1] for row in cursor.fetchall()}

    # --- Teacher ranking ---
    cursor.execute("""
        SELECT T.Name, COUNT(B.BookingID)
        FROM Bookings B
        JOIN Teachers T ON B.TeacherID = T.TeacherID
        WHERE B.Status = 'Approved'
        GROUP BY T.Name
        ORDER BY COUNT(B.BookingID) DESC
    """)
    teacher_ranking = cursor.fetchall()

    # --- Subject ranking ---
    cursor.execute("""
        SELECT T.Subject, COUNT(B.BookingID)
        FROM Bookings B
        JOIN Teachers T ON B.TeacherID = T.TeacherID
        WHERE B.Status = 'Approved'
        GROUP BY T.Subject
        ORDER BY COUNT(B.BookingID) DESC
    """)
    subject_ranking = cursor.fetchall()

    # --- Teacher list ---
    cursor.execute("""
        SELECT T.Name, T.Email, T.Phone, 
               COUNT(B.BookingID) AS Bookings
        FROM Teachers T
        LEFT JOIN Bookings B ON T.TeacherID = B.TeacherID
        GROUP BY T.TeacherID
    """)
    teacher_list = [
        dict(Name=row[0], Email=row[1], Phone=row[2], Bookings=row[3])
        for row in cursor.fetchall()
    ]

    conn.close()

    # --- Current date/time ---
    now = datetime.now()

    return render_template(
        'admin/report.html',
        now=now,
        summary=summary,
        teacher_ranking=teacher_ranking,
        subject_ranking=subject_ranking,
        teacher_list=teacher_list
    )





@app.route('/admin/analysis')
def analysis():
    conn = connect_db()
    cursor = conn.cursor()

    # Booking summary
    cursor.execute("SELECT Status, COUNT(*) FROM Bookings GROUP BY Status")
    summary = {row[0]: row[1] for row in cursor.fetchall()}

    # Teacher ranking
    cursor.execute("""
        SELECT T.Name, COUNT(B.BookingID)
        FROM Bookings B
        JOIN Teachers T ON B.TeacherID = T.TeacherID
        WHERE B.Status = 'Approved'
        GROUP BY T.Name
        ORDER BY COUNT(B.BookingID) DESC
    """)
    teacher_ranking = cursor.fetchall()

    # Subject ranking
    cursor.execute("""
        SELECT T.Subject, COUNT(B.BookingID)
        FROM Bookings B
        JOIN Teachers T ON B.TeacherID = T.TeacherID
        WHERE B.Status = 'Approved'
        GROUP BY T.Subject
        ORDER BY COUNT(B.BookingID) DESC
    """)
    subject_ranking = cursor.fetchall()

    conn.close()

    return render_template(
        'admin/anlysis.html',
        summary=summary,
        teacher_ranking=teacher_ranking,
        subject_ranking=subject_ranking,
        teacher_labels=[t[0] for t in teacher_ranking],
        teacher_counts=[t[1] for t in teacher_ranking],
        subject_labels=[s[0] for s in subject_ranking],
        subject_counts=[s[1] for s in subject_ranking],
        status_labels=list(summary.keys()),
        status_counts=list(summary.values())
    )


@app.route('/view_all_request')
def view_all_requests():
    """
    Fetches and displays all classroom booking requests.
    Note: This endpoint is publicly accessible as requested (no decorators).
    """
    try:
        # 1. Fetch all bookings using the existing function
        # This function should return a list of all booking records (Approved, Pending, Denied)
        all_bookings = get_all_bookings()
        
        # 2. Render the template and pass the data
        return render_template('all_requests.html', bookings=all_bookings)
        
    except Exception as e:
        # Handle potential errors (e.g., database connection failure)
        flash(f"An error occurred while fetching requests: {e}", 'danger')
        # Redirect back to the main booking page or a safe default
        return redirect(url_for('book_classroom')) 
    # app.py

# Ensure get_all_classrooms is imported from smart_scheduler
# ... (app.py)
# Assuming get_all_teachers is in a file named 'smart_scheduler.py'



@app.route('/add-columns-fix')
def add_db_columns():
    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Add Gender column
        

        # You should also add the other missing columns (Email, Phone, ClassTeacher)
        # based on the previous context, or your application will fail later.
       
        cursor.execute("ALTER TABLE Teachers ADD COLUMN ClassTeacher TEXT;")

        conn.commit()
        conn.close()
        return "Database columns added successfully: Gender, Email, Phone, ClassTeacher."
    except sqlite3.OperationalError as e:
        # This handles the error if the columns already exist
        conn.close()
        return f"Error (Columns likely already exist): {e}", 500  


@app.route('/bookings/new', methods=['GET', 'POST'])
def bookings():
    conn = connect_db()
    cursor = conn.cursor()

    # ✅ Fetch classrooms with correct column name
    cursor.execute("SELECT RoomID, Name, EquipmentList FROM Classrooms")
    classrooms = cursor.fetchall()

    if request.method == 'POST':
        # ✅ Get logged-in teacher info from session
        teacher_id = session.get('user_id')
        username = session.get('username')

        room_id = request.form.get('room_id')
        date = request.form.get('date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        equipment = request.form.get('equipment', '').strip()
        status = 'Pending'

        # ✅ Validation
        if not (teacher_id and room_id and date and start_time and end_time):
            flash("Please fill in all required fields.", "danger")
        else:
            try:
                cursor.execute("""
                    INSERT INTO Bookings (TeacherID, RoomID, Date, StartTime, EndTime, Equipment, Status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (teacher_id, room_id, date, start_time, end_time, equipment, status))
                conn.commit()
                flash(f"Booking created successfully by {username} and marked as Pending!", "success")
                return redirect(url_for('bookings'))
            except sqlite3.Error as e:
                flash(f"Database error: {e}", "danger")

    conn.close()
    # ✅ Use "classrooms" variable to match template
    return render_template('bookings.html', classrooms=classrooms)



@app.route('/booking/<int:booking_id>/cancel', methods=['POST', 'GET'])
def cancel_booking(booking_id):
    # Logic to cancel the booking
    return redirect(url_for('manage_bookings'))



@app.route("/admin/all_bookings")
def admin_all_bookings():
    """
    Fetches all bookings from the database,
    joining with Teachers and Classrooms tables
    to show readable information, with pagination.
    """
    conn = connect_db()
    cursor = conn.cursor()

    # Pagination settings
    page = request.args.get('page', 1, type=int)  # Current page
    per_page = 10  # Number of bookings per page
    offset = (page - 1) * per_page

    # Fetch paginated bookings with teacher subject
    cursor.execute("""
        SELECT 
            B.BookingID,
            T.Name AS TeacherName,
            T.Subject AS TeacherSubject,
            C.Name AS RoomName,
            B.Date,
            B.StartTime,
            B.EndTime,
            B.Equipment,
            B.Status
        FROM Bookings B
        JOIN Teachers T ON B.TeacherID = T.TeacherID
        JOIN Classrooms C ON B.RoomID = C.RoomID
        ORDER BY B.Date DESC, B.StartTime ASC
        LIMIT ? OFFSET ?
    """, (per_page, offset))

    bookings = [
        dict(
            BookingID=row[0],
            TeacherName=row[1],
            Subject=row[2],
            RoomName=row[3],
            Date=row[4],
            StartTime=row[5],
            EndTime=row[6],
            Equipment=row[7],
            Status=row[8],
        )
        for row in cursor.fetchall()
    ]

    # Get total number of bookings for pagination
    cursor.execute("SELECT COUNT(*) FROM Bookings")
    total_bookings = cursor.fetchone()[0]
    total_pages = ceil(total_bookings / per_page)

    conn.close()

    return render_template(
        "admin_all_bookings.html",
        bookings=bookings,
        page=page,
        total_pages=total_pages,
        now=datetime.now()
    )




@app.route('/booking_reports')
def booking_reports():
    conn = connect_db()
    cursor = conn.cursor()

    # --- Status Summary ---
    cursor.execute("SELECT Status FROM Bookings")
    bookings_status = cursor.fetchall()
    status_list = [b[0] for b in bookings_status if b[0]]  # remove None
    status_summary = Counter(status_list)

    status_labels = list(status_summary.keys()) if status_summary else []
    status_counts = list(status_summary.values()) if status_summary else []
    total_status = sum(status_counts)
    status_percentages = [(count / total_status * 100) if total_status > 0 else 0 for count in status_counts]

    # Prepare a list of tuples for Jinja
    status_summary_list = list(zip(status_labels, status_counts, status_percentages))

    # --- Top Teachers ---
    cursor.execute("""
        SELECT t.Name, COUNT(*) as count
        FROM Bookings b
        JOIN Teachers t ON b.TeacherID = t.TeacherID
        WHERE b.Status='Approved'
        GROUP BY t.Name
        ORDER BY count DESC
    """)
    teacher_ranking = cursor.fetchall() or []
    teacher_labels = [t[0] for t in teacher_ranking]
    teacher_counts = [t[1] for t in teacher_ranking]

    # --- Top Subjects ---
    cursor.execute("""
        SELECT t.Subject, COUNT(*) as count
        FROM Bookings b
        JOIN Teachers t ON b.TeacherID = t.TeacherID
        WHERE b.Status='Approved'
        GROUP BY t.Subject
        ORDER BY count DESC
    """)
    subject_ranking = cursor.fetchall() or []
    subject_labels = [s[0] for s in subject_ranking]
    subject_counts = [s[1] for s in subject_ranking]

    conn.close()

    return render_template(
        'usage_reports.html',
        status_summary_list=status_summary_list,
        status_labels=status_labels,
        status_counts=status_counts,
        teacher_ranking=teacher_ranking,
        teacher_labels=teacher_labels,
        teacher_counts=teacher_counts,
        subject_ranking=subject_ranking,
        subject_labels=subject_labels,
        subject_counts=subject_counts
    )

# EDIT BOOKING ENDPOINT
@app.route('/edit_booking/<int:booking_id>', methods=['GET', 'POST'])
def edit_booking(booking_id):
    conn = connect_db()
    cursor = conn.cursor()

    # Fetch the booking details along with teacher info
    cursor.execute("""
        SELECT 
            B.BookingID,
            B.TeacherID,
            T.Name AS TeacherName,
            T.Subject AS TeacherSubject,
            B.RoomID,
            B.Date,
            B.StartTime,
            B.EndTime,
            B.Equipment,
            B.Status
        FROM Bookings B
        JOIN Teachers T ON B.TeacherID = T.TeacherID
        WHERE B.BookingID = ?
    """, (booking_id,))
    booking = cursor.fetchone()

    if not booking:
        flash("Booking not found.", "danger")
        conn.close()
        return redirect(url_for('manage_bookings'))

    if request.method == 'POST':
        # Get form data
        date = request.form.get('date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        equipment = request.form.get('equipment')
        status = request.form.get('status')

        # Update booking
        cursor.execute("""
            UPDATE Bookings
            SET Date = ?, StartTime = ?, EndTime = ?, Equipment = ?, Status = ?
            WHERE BookingID = ?
        """, (date, start_time, end_time, equipment, status, booking_id))
        conn.commit()
        conn.close()
        flash("Booking updated successfully.", "success")
        return redirect(url_for('admin_all_bookings'))

    conn.close()

    # Prepare data for template
    booking_data = {
        "BookingID": booking[0],
        "TeacherID": booking[1],
        "TeacherName": booking[2],
        "TeacherSubject": booking[3],
        "RoomID": booking[4],
        "Date": booking[5],
        "StartTime": booking[6],
        "EndTime": booking[7],
        "Equipment": booking[8],
        "Status": booking[9]
    }

    # Status options
    status_options = ['Pending', 'Approved', 'Denied']

    return render_template(
        'edit_booking.html',
        booking=booking_data,
        status_options=status_options
    )

@app.route('/delete_booking/<int:booking_id>', methods=['POST'])
def delete_booking(booking_id):
    conn = connect_db()
    cursor = conn.cursor()

    # Check if booking exists
    cursor.execute("SELECT * FROM Bookings WHERE BookingID = ?", (booking_id,))
    booking = cursor.fetchone()
    if not booking:
        conn.close()
        flash("Booking not found.", "danger")
        return redirect(url_for('manage_bookings'))

    # Delete the booking
    cursor.execute("DELETE FROM Bookings WHERE BookingID = ?", (booking_id,))
    conn.commit()
    conn.close()

    flash(f"Booking #{booking_id} has been deleted.", "success")
    return redirect(url_for('manage_bookings'))
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/request_material', methods=['GET', 'POST'])
def request_material():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        gender = request.form.get('gender')
        phone_number = request.form.get('phone_number')
        class_teacher = request.form.get('class_teacher')
        material_name = request.form.get('material_name')
        borrowed_date = request.form.get('borrowed_date')
        returned_date = request.form.get('returned_date')
        reason = request.form.get('reason')

        # File upload
        letter_file = request.files.get('letter_file')
        if not letter_file or not allowed_file(letter_file.filename):
            flash("Please upload a valid permission letter (.pdf, .doc, .docx)", "danger")
            return redirect(request.url)

        filename = secure_filename(f"{full_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{letter_file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        letter_file.save(filepath)

        # Save to database
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO MaterialRequests 
            (FullName, Gender, PhoneNumber, ClassTeacher, MaterialName, BorrowedDate, ReturnedDate, Reason, LetterFile)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (full_name, gender, phone_number, class_teacher, material_name, borrowed_date, returned_date, reason, filename))
        conn.commit()
        conn.close()

        flash("Material request submitted successfully!", "success")
        return redirect(url_for('request_material'))

    return render_template('request_material.html')

@app.route('/admin/material_requests')
def admin_material_requests():
    conn = connect_db()
    conn.row_factory = sqlite3.Row  # <-- Make rows dict-like
    cursor = conn.cursor()

    # Get filters
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 10  # Number of requests per page
    offset = (page - 1) * per_page

    # Base query
    query = "SELECT * FROM MaterialRequests WHERE 1=1"
    params = []

    # Apply search filter
    if search:
        query += " AND FullName LIKE ?"
        params.append(f"%{search}%")

    # Apply status filter
    if status:
        query += " AND Status = ?"
        params.append(status)

    # Count total results for pagination
    total_query = f"SELECT COUNT(*) FROM ({query})"
    cursor.execute(total_query, params)
    total_records = cursor.fetchone()[0]
    total_pages = max(1, (total_records + per_page - 1) // per_page)

    # Fetch paginated results ordered by CreatedAt
    query += " ORDER BY CreatedAt DESC LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    cursor.execute(query, params)
    requests = cursor.fetchall()  # Each row is now dict-like

    conn.close()

    return render_template(
        'admin_material_requests.html',
        requests=requests,
        page=page,
        total_pages=total_pages,
        search=search,
        status=status
    )
@app.route('/material_requests')
def material_requests():
    conn = connect_db()
    conn.row_factory = sqlite3.Row  # <-- Make rows dict-like
    cursor = conn.cursor()

    # Get filters
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 10  # Number of requests per page
    offset = (page - 1) * per_page

    # Base query
    query = "SELECT * FROM MaterialRequests WHERE 1=1"
    params = []

    # Apply search filter
    if search:
        query += " AND FullName LIKE ?"
        params.append(f"%{search}%")

    # Apply status filter
    if status:
        query += " AND Status = ?"
        params.append(status)

    # Count total results for pagination
    total_query = f"SELECT COUNT(*) FROM ({query})"
    cursor.execute(total_query, params)
    total_records = cursor.fetchone()[0]
    total_pages = max(1, (total_records + per_page - 1) // per_page)

    # Fetch paginated results ordered by CreatedAt
    query += " ORDER BY CreatedAt DESC LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    cursor.execute(query, params)
    requests = cursor.fetchall()  # Each row is now dict-like

    conn.close()

    return render_template(
        'material_requests.html',
        requests=requests,
        page=page,
        total_pages=total_pages,
        search=search,
        status=status
    )     


@app.route('/admin/approve_material/<int:request_id>')
def approve_material(request_id):
    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Check if the record exists
        cursor.execute("SELECT * FROM MaterialRequests WHERE RequestID=?", (request_id,))
        record = cursor.fetchone()

        if not record:
            flash("⚠️ Material request not found!", "warning")
        else:
            # Update only the Status column since ApprovedDate doesn't exist
            cursor.execute("""
                UPDATE MaterialRequests 
                SET Status = 'Approved'
                WHERE RequestID = ?
            """, (request_id,))
            conn.commit()
            flash(f"✅ Material request #{request_id} approved successfully!", "success")
    except Exception as e:
        flash(f"❌ Error approving request: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for('admin_material_requests'))

# ❌ Admin rejects material request
@app.route('/admin/reject_material/<int:request_id>')
def reject_material(request_id):
    try:
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM MaterialRequests WHERE RequestID=?", (request_id,))
        record = cursor.fetchone()

        if not record:
            flash("Material request not found!", "warning")
        else:
            cursor.execute("""
                UPDATE MaterialRequests 
                SET Status='Rejected', RejectedDate=? 
                WHERE RequestID=?
            """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), request_id))
            conn.commit()
            flash(f"🚫 Material request #{request_id} rejected!", "danger")
    except Exception as e:
        flash(f"Error rejecting request: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for('admin_material_requests'))
@app.route('/admin/export_material_requests')
def export_material_requests():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            MR.RequestID, 
            MR.FullName, 
            MR.Gender, 
            MR.PhoneNumber, 
            MR.ClassTeacher,
            MR.MaterialName, 
            MR.BorrowedDate, 
            MR.ReturnedDate,
            MR.Reason, 
            MR.Status, 
            MR.CreatedAt
        FROM MaterialRequests MR
        ORDER BY MR.CreatedAt DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    # Prepare CSV content
    header = [
        "Request ID", "Full Name", "Gender", "Phone", "Class Teacher",
        "Material", "Borrowed Date", "Return Date", "Reason", "Status", "Created At"
    ]
    csv_lines = [",".join(header)]

    for row in rows:
        csv_lines.append(",".join([str(item) if item is not None else "" for item in row]))

    # Generate response
    output = "\n".join(csv_lines)
    response = make_response(output)
    response.headers["Content-Disposition"] = "attachment; filename=Material_Requests_Report.csv"
    response.headers["Content-type"] = "text/csv"
    return response

# ✅ Upload Teacher Document Route
@app.route('/upload_teacher_document', methods=['GET', 'POST'])
def upload_teacher_document():
    # ✅ Check login session
    if 'user_id' not in session or session.get('role') not in ['Teacher', 'ICT_Admin', 'Deputy']:
        flash("Please log in with a valid account.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        document_type = request.form.get('document_type')
        file = request.files.get('file')

        if not file or file.filename.strip() == "":
            flash("Please select a file to upload.", "danger")
            return redirect(url_for('upload_teacher_document'))

        # ✅ Create upload folder (if it doesn’t exist)
        upload_folder = os.path.join(app.root_path, 'static', 'teacher_documents')
        os.makedirs(upload_folder, exist_ok=True)

        # ✅ Secure the filename and save file
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)

        # ✅ Save document info into database
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO TeacherDocuments (TeacherID, DocumentType, FilePath, UploadDate)
            VALUES (?, ?, ?, datetime('now'))
        """, (session['user_id'], document_type, filename))
        conn.commit()
        conn.close()

        flash("Document uploaded successfully!", "success")
        return redirect(url_for('upload_teacher_document'))

    # ✅ Render upload form page
    return render_template('upload_teacher_document.html')

@app.route('/deputy_documents', methods=['GET', 'POST'])
def deputy_documents():
    """
    Deputy view:
    - Lists all teacher documents.
    - Allows filtering by SubmitDate.
    - Displays data for deputy_documents.html with countdowns and status badges.
    """
    filter_date = None
    documents = []

    try:
        if request.method == "POST":
            filter_date = request.form.get("filter_date") or None

        conn = connect_db()
        cursor = conn.cursor()

        # ✅ Query to fetch all columns from TeacherDocuments
        if filter_date:
            cursor.execute("""
                SELECT 
                    DocumentID, TeacherID, DocumentType, FilePath,
                    SubmitDate, SubmitTime, Status, UploadDate
                FROM TeacherDocuments
                WHERE SubmitDate = ?
                ORDER BY UploadDate DESC
            """, (filter_date,))
        else:
            cursor.execute("""
                SELECT 
                    DocumentID, TeacherID, DocumentType, FilePath,
                    SubmitDate, SubmitTime, Status, UploadDate
                FROM TeacherDocuments
                ORDER BY UploadDate DESC
            """)

        documents = cursor.fetchall()

    except sqlite3.Error as e:
        flash(f"Database error: {e}", "danger")

    finally:
        if conn:
            conn.close()

    return render_template(
        "deputy_documents.html",  # Make sure this matches your updated template
        documents=documents,
        filter_date=filter_date
    )


from datetime import datetime

# ---------- Approve / Deny Teacher Document ----------
@app.route('/deputy/approve/<int:document_id>')
def deputy_approve_doc(document_id):
    """
    Approve a document in TeacherDocuments table
    """
    try:
        conn = connect_db()
        cursor = conn.cursor()
        approved_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            UPDATE TeacherDocuments
            SET Status = 'Approved', UploadDate = ?
            WHERE DocumentID = ?
        """, (approved_date, document_id))

        conn.commit()
        flash("✅ Document approved successfully.", "success")

    except Exception as e:
        flash(f"Error approving document: {e}", "danger")

    finally:
        if conn:
            conn.close()

    return redirect(url_for('deputy_documents'))  # make sure this is your updated page



@app.route('/deputy/deny/<int:document_id>')
def deputy_deny_doc(document_id):
    """
    Deny a document in TeacherDocuments table
    """
    try:
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE TeacherDocuments
            SET Status = 'Denied', UploadDate = NULL
            WHERE DocumentID = ?
        """, (document_id,))

        conn.commit()
        flash("❌ Document denied successfully.", "info")

    except Exception as e:
        flash(f"Error denying document: {e}", "danger")

    finally:
        if conn:
            conn.close()

    return redirect(url_for('deputy_documents'))  # make sure this matches your listing page



# ---------- Download Uploaded File ----------
@app.route('/deputy/download/<path:filename>')
def download_file(filename):
    """Allows Deputy to download uploaded LetterFile."""
    try:
        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
    except Exception as e:
        flash(f"Error downloading file: {e}", "danger")
        return redirect(url_for('deputy_requests'))
@app.route("/admin/deputies")
def manage_deputies():
    if session.get("role") != "ICT_Admin":
        flash("Access denied!", "danger")
        return redirect(url_for("login"))

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT TeacherID, Name, Username, Role, IsApproved FROM Teachers WHERE Role='Deputy'")
    deputies = cursor.fetchall()
    conn.close()
    return render_template("manage_deputies.html", deputies=deputies)


@app.route("/admin/deputy/add", methods=["GET", "POST"])
def add_deputy():
    if session.get("role") != "ICT_Admin":
        flash("Access denied!", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("name")
        username = request.form.get("username")
        password = request.form.get("password")

        hashed_password = generate_password_hash(password)
        result = register_deputy(name, username, hashed_password)
        if result is True:
            flash("Deputy registered successfully.", "success")
            return redirect(url_for("manage_deputies"))
        else:
            flash(result, "danger")

    return render_template("add_deputy.html")


@app.route("/admin/deputy/delete/<int:teacher_id>")
def delete_deputy(teacher_id):
    if session.get("role") != "ICT_Admin":
        flash("Access denied!", "danger")
        return redirect(url_for("login"))

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Teachers WHERE TeacherID = ? AND Role='Deputy'", (teacher_id,))
    conn.commit()
    conn.close()
    flash("Deputy deleted successfully.", "success")
    return redirect(url_for("manage_deputies"))



# -----------------------
# DASHBOARD & LOGOUT
# -----------------------
@app.route("/deputy_dashboard")
def deputy_dashboard():
    if "role" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    role = session["role"]
    return render_template("deputy_dashboard.html", role=role)

def create_default_deputy(username="deputy", password="Deputy@123", name="Deputy of Studies"):
    """
    Creates a default Deputy account if it doesn't exist.
    Stores password in plain text.
    Prints confirmation if created.
    """
    conn = connect_db()
    if not conn:
        print("[ERROR] DB connection failed.")
        return False

    try:
        cursor = conn.cursor()
        # Check if deputy already exists
        cursor.execute("SELECT TeacherID FROM Teachers WHERE Username = ?", (username,))
        if cursor.fetchone():
            print(f"[INFO] Default deputy '{username}' already exists. ✅")
            return True

        # Insert default deputy
        cursor.execute("""
            INSERT INTO Teachers (Name, Username, Password, Role, IsApproved)
            VALUES (?, ?, ?, 'Deputy', 1)
        """, (name, username, password))
        conn.commit()

        print(f"[SUCCESS] Default deputy created!")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print("⚠️ Please change the password after first login.")
        return True

    except sqlite3.Error as e:
        print(f"[ERROR] Could not create default deputy: {e}")
        return False
    finally:
        conn.close()

@app.route('/show_database')
def show_database():
    """
    Display all tables and their rows from the SQLite database.
    """
    conn = connect_db()
    tables = {}
    try:
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        table_names = [row[0] for row in cursor.fetchall()]

        # Fetch all rows for each table
        for table in table_names:
            cursor.execute(f"PRAGMA table_info({table});")
            columns = [col[1] for col in cursor.fetchall()]  # column names

            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()

            tables[table] = {
                "columns": columns,
                "rows": rows
            }
    except sqlite3.Error as e:
        flash(f"Database error: {e}", "danger")
    finally:
        if conn:
            conn.close()

    return render_template('show_database.html', tables=tables)
@app.route('/deputy/reports')
def deputy_reports():
    """
    Render a report page showing charts and table of document status percentages
    """
    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Total documents
        cursor.execute("SELECT COUNT(*) FROM TeacherDocuments")
        total_docs = cursor.fetchone()[0] or 1

        # Count documents per status
        cursor.execute("SELECT Status, COUNT(*) FROM TeacherDocuments GROUP BY Status")
        status_counts = cursor.fetchall()

        # Prepare report data with percentages
        report_data = []
        for status, count in status_counts:
            percentage = round((count / total_docs) * 100, 2)
            report_data.append({
                "status": status,
                "count": count,
                "percentage": percentage
            })

        # Sort descending by percentage for ranking
        report_data.sort(key=lambda x: x["percentage"], reverse=True)

    finally:
        if conn:
            conn.close()

    return render_template(
        "deputy_reports.html",
        report_data=report_data
    )

if __name__ == '__main__':
    # Initialize the database file if it doesn't exist (assuming db_setup.py is run)
    if not os.path.exists(DB_FILE):
        print(f"WARNING: Database file '{DB_FILE}' not found. Please run db_setup.py script first.")

      
    app.run(host="127.0.0.1", port=5000, debug=True)