"""
auth.py
=======
Authentication, Session Management, and Role-Based Access Control (RBAC).

Features:
- Secure password hashing and verification via Werkzeug security primitives.
- Session-based authentication with role identification.
- Strict server-side route protection decorators:
    - @login_required: Enforces active session.
    - @roles_required(*roles): Enforces authorized roles ('admin', 'doctor', 'patient').
- Automatic role metadata lookup (links doctor_id or patient_id to session).
- Generic login failure responses to prevent username enumeration attacks.
"""

from functools import wraps
from typing import Optional, Dict, Any, List, Tuple
from flask import session, redirect, url_for, flash, request, abort, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection
from audit_service import record_audit_event
from validators import validate_username, validate_password, validate_email, VALID_ROLES
from blockchain import get_current_utc_timestamp


def authenticate_user(username: str, password: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Verifies user credentials.
    Returns the user dict if valid and active, otherwise None.
    Uses constant-time comparison via check_password_hash to prevent timing attacks.
    """
    if not username or not password:
        return None

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?;", (username.strip(),))
        user = cursor.fetchone()
        if not user:
            return None

        if not user["is_active"]:
            return None

        if check_password_hash(user["password_hash"], password):
            return dict(user)
        return None
    finally:
        conn.close()


def login_user(user: Dict[str, Any], db_path: Optional[str] = None) -> None:
    """
    Initializes the session with user credentials and associated role profiles.
    """
    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    session["full_name"] = user["full_name"]
    session["email"] = user["email"]

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        if user["role"] == "patient":
            cursor.execute("SELECT id, patient_code FROM patients WHERE user_id = ?;", (user["id"],))
            pat = cursor.fetchone()
            if pat:
                session["patient_id"] = pat["id"]
                session["patient_code"] = pat["patient_code"]
        elif user["role"] == "doctor":
            cursor.execute("SELECT id, doctor_code, specialization FROM doctors WHERE user_id = ?;", (user["id"],))
            doc = cursor.fetchone()
            if doc:
                session["doctor_id"] = doc["id"]
                session["doctor_code"] = doc["doctor_code"]
                session["specialization"] = doc["specialization"]
    finally:
        conn.close()


def logout_user() -> None:
    """Clears all session variables."""
    session.clear()


def is_authenticated() -> bool:
    """Returns True if a user is currently logged in."""
    return "user_id" in session and session.get("user_id") is not None


def get_current_user_role() -> Optional[str]:
    """Returns the role of the currently logged-in user, or None."""
    return session.get("role")


def login_required(f):
    """Decorator ensuring that only authenticated users can access the endpoint."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def roles_required(*allowed_roles):
    """
    Decorator enforcing that the logged-in user has one of the specified roles.
    Hiding buttons on the client is insufficient; this provides server-side enforcement.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_authenticated():
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("login", next=request.url))
            
            user_role = session.get("role")
            if user_role not in allowed_roles:
                return render_template(
                    "access_denied.html",
                    required_roles=list(allowed_roles),
                    current_role=user_role
                ), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def register_user(
    username: str,
    password: str,
    role: str,
    full_name: str,
    email: str,
    actor_user_id: Optional[int] = None,
    ip_address: str = "127.0.0.1",
    db_path: Optional[str] = None,
    doctor_code: Optional[str] = None,
    specialization: Optional[str] = None,
    license_number: Optional[str] = None,
    patient_code: Optional[str] = None,
    date_of_birth: Optional[str] = None,
    gender: Optional[str] = None,
    blood_group: Optional[str] = None,
    contact_phone: Optional[str] = None,
    address: Optional[str] = None,
    emergency_contact: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Registers a new user with password hashing, creates associated Doctor or Patient
    profiles, and writes an audit log.
    """
    # 1. Validate inputs
    u_ok, u_err = validate_username(username)
    if not u_ok:
        return False, u_err, None

    p_ok, p_err = validate_password(password)
    if not p_ok:
        return False, p_err, None

    e_ok, e_err = validate_email(email)
    if not e_ok:
        return False, e_err, None

    if role not in VALID_ROLES:
        return False, f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}", None

    if not full_name or not full_name.strip():
        return False, "Full name is required.", None

    conn = get_db_connection(db_path)
    now_ts = get_current_utc_timestamp()

    try:
        with conn:
            cursor = conn.cursor()
            # Check unique username and email
            cursor.execute("SELECT id FROM users WHERE username = ?;", (username.strip(),))
            if cursor.fetchone():
                return False, f"Username '{username}' is already registered.", None

            cursor.execute("SELECT id FROM users WHERE email = ?;", (email.strip(),))
            if cursor.fetchone():
                return False, f"Email '{email}' is already registered.", None

            pwd_hash = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, full_name, email, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            """, (username.strip(), pwd_hash, role, full_name.strip(), email.strip(), now_ts))
            new_id = cursor.lastrowid

            # Create associated clinical profiles
            if role == "doctor":
                cursor.execute("SELECT COUNT(*) AS cnt FROM doctors;")
                doc_count = cursor.fetchone()["cnt"]
                d_code = doctor_code.strip() if doctor_code and doctor_code.strip() else f"DOC-{101 + doc_count}"
                spec = specialization.strip() if specialization and specialization.strip() else "General Medicine"
                lic = license_number.strip() if license_number and license_number.strip() else f"MCI-2026-{1000 + new_id}"
                phone = contact_phone.strip() if contact_phone and contact_phone.strip() else "+91-98765-00000"

                cursor.execute("""
                    INSERT INTO doctors (user_id, doctor_code, specialization, license_number, contact_phone, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (new_id, d_code, spec, lic, phone, now_ts))

            elif role == "patient":
                cursor.execute("SELECT COUNT(*) AS cnt FROM patients;")
                pat_count = cursor.fetchone()["cnt"]
                p_code = patient_code.strip() if patient_code and patient_code.strip() else f"PAT-{1001 + pat_count}"
                dob = date_of_birth.strip() if date_of_birth and date_of_birth.strip() else "1995-01-01"
                gen = gender.strip() if gender and gender.strip() else "Male"
                bg = blood_group.strip() if blood_group and blood_group.strip() else "O+"
                phone = contact_phone.strip() if contact_phone and contact_phone.strip() else "+91-91234-00000"
                addr = address.strip() if address and address.strip() else "Local Resident, City Center"
                emerg = emergency_contact.strip() if emergency_contact and emergency_contact.strip() else "Emergency Kin (+91-91234-99999)"

                cursor.execute("""
                    INSERT INTO patients (
                        user_id, patient_code, date_of_birth, gender, blood_group,
                        contact_phone, address, emergency_contact, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (new_id, p_code, dob, gen, bg, phone, addr, emerg, now_ts))

            # Audit log
            record_audit_event(
                cursor_or_conn=cursor,
                action="USER_REGISTERED",
                entity_type="USER",
                entity_id=str(new_id),
                ip_address=ip_address,
                details=f"New {role} '{username}' ({full_name}) registered successfully.",
                actor_user_id=actor_user_id,
                timestamp=now_ts
            )

            return True, None, new_id
    except Exception as e:
        return False, f"Registration failed: {str(e)}", None
    finally:
        conn.close()


def get_all_users(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns a list of all users excluding password hashes."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, role, full_name, email, is_active, created_at
            FROM users
            ORDER BY id ASC;
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_all_patients(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns all patients joined with their user account metadata."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                p.id,
                p.user_id,
                p.patient_code,
                u.full_name,
                u.email,
                p.date_of_birth,
                p.gender,
                p.blood_group,
                p.contact_phone,
                p.address,
                p.emergency_contact,
                p.created_at
            FROM patients p
            JOIN users u ON p.user_id = u.id
            ORDER BY p.id ASC;
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_patient_by_id(patient_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Returns detailed patient profile by patient_id."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                p.id,
                p.user_id,
                p.patient_code,
                u.full_name,
                u.email,
                p.date_of_birth,
                p.gender,
                p.blood_group,
                p.contact_phone,
                p.address,
                p.emergency_contact,
                p.created_at
            FROM patients p
            JOIN users u ON p.user_id = u.id
            WHERE p.id = ?;
        """, (patient_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_doctor_by_user_id(user_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Returns doctor profile corresponding to a user account."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.id, d.user_id, d.doctor_code, u.full_name, d.specialization, d.license_number, d.contact_phone
            FROM doctors d
            JOIN users u ON d.user_id = u.id
            WHERE d.user_id = ?;
        """, (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_patient_by_user_id(user_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Returns patient profile corresponding to a user account."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.user_id, p.patient_code, u.full_name, p.date_of_birth, p.gender, p.blood_group, p.contact_phone, p.address, p.emergency_contact
            FROM patients p
            JOIN users u ON p.user_id = u.id
            WHERE p.user_id = ?;
        """, (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
