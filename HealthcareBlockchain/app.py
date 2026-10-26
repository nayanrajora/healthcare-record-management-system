"""
app.py
======
Main Flask Application for the Healthcare Record Management System Using Blockchain Technology.

Features:
- Session-based Role-Based Access Control (RBAC).
- CSRF Protection via Flask-WTF.
- Cryptographic hash chaining and dual-phase verification.
- Tamper simulation workbench for college viva presentation.
- Complete audit logging and safe parameterization.
"""

import os
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, abort
)
from flask_wtf.csrf import CSRFProtect

from config import Config
from database import get_db_connection, init_db, seed_demo_data
from blockchain import verify_chain
from auth import (
    authenticate_user, login_user, logout_user, is_authenticated,
    login_required, roles_required, register_user, get_all_users,
    get_all_patients, get_patient_by_id, get_doctor_by_user_id,
    get_patient_by_user_id
)
from record_service import (
    create_medical_record, update_medical_record, get_medical_record_by_id,
    get_record_versions, get_records_for_patient, get_records_for_doctor,
    get_all_records, verify_medical_record_integrity, fetch_record_version_for_blockchain
)
from audit_service import record_audit_event, get_audit_logs, get_total_audit_logs_count


def create_app(config_class=Config) -> Flask:
    """Application factory initializing extensions, database schema, and route blueprints."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize CSRF Protection
    csrf = CSRFProtect(app)

    # Automatically ensure database and initial demo seed exists
    with app.app_context():
        try:
            init_db(app.config["DATABASE_PATH"])
            seed_demo_data(app.config["DATABASE_PATH"])
        except Exception as e:
            app.logger.warning(f"Database initialization check notice: {e}")

    # Context Processors for Templates
    @app.context_processor
    def inject_global_template_vars():
        return {
            "current_user_role": session.get("role"),
            "current_username": session.get("username"),
            "current_user_full_name": session.get("full_name")
        }

    # Helper for client IP
    def get_client_ip():
        return request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1")

    # -------------------------------------------------------------
    # Authentication & Dashboard Routes
    # -------------------------------------------------------------

    @app.route("/")
    def index():
        """Root route: redirects authenticated users to their dashboard, otherwise login."""
        if is_authenticated():
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """Handles user sign in with generic failure alerts and audit logs."""
        if is_authenticated():
            return redirect(url_for("dashboard"))

        next_url = request.args.get("next")
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            next_url = request.form.get("next")

            user = authenticate_user(username, password, app.config["DATABASE_PATH"])
            if user:
                login_user(user, app.config["DATABASE_PATH"])
                conn = get_db_connection(app.config["DATABASE_PATH"])
                try:
                    record_audit_event(
                        cursor_or_conn=conn,
                        action="LOGIN_SUCCESS",
                        entity_type="USER",
                        entity_id=str(user["id"]),
                        ip_address=get_client_ip(),
                        details=f"User '{username}' successfully logged in with role '{user['role']}'.",
                        actor_user_id=user["id"]
                    )
                finally:
                    conn.close()
                flash(f"Welcome back, {user['full_name']}!", "success")

                if next_url and next_url.startswith("/"):
                    return redirect(next_url)
                return redirect(url_for("dashboard"))
            else:
                # Generic error prevents username enumeration
                conn = get_db_connection(app.config["DATABASE_PATH"])
                try:
                    record_audit_event(
                        cursor_or_conn=conn,
                        action="LOGIN_FAILED",
                        entity_type="AUTH",
                        entity_id=None,
                        ip_address=get_client_ip(),
                        details=f"Failed login attempt for username '{username}'."
                    )
                finally:
                    conn.close()
                flash("Invalid username or password. Please try again.", "danger")

        return render_template("login.html", next_url=next_url)

    @app.route("/logout", methods=["POST"])
    def logout():
        """Securely logs the user out, records audit log, and clears session."""
        if is_authenticated():
            u_id = session.get("user_id")
            u_name = session.get("username")
            conn = get_db_connection(app.config["DATABASE_PATH"])
            try:
                record_audit_event(
                    cursor_or_conn=conn,
                    action="LOGOUT",
                    entity_type="USER",
                    entity_id=str(u_id),
                    ip_address=get_client_ip(),
                    details=f"User '{u_name}' logged out.",
                    actor_user_id=u_id
                )
            finally:
                conn.close()
        logout_user()
        flash("You have been signed out successfully.", "info")
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        """Role-based router dispatching to respective role portals."""
        role = session.get("role")
        if role == "admin":
            return redirect(url_for("admin_dashboard"))
        elif role == "doctor":
            return redirect(url_for("doctor_dashboard"))
        elif role == "patient":
            return redirect(url_for("patient_dashboard"))
        return redirect(url_for("login"))

    @app.route("/admin/dashboard")
    @roles_required("admin")
    def admin_dashboard():
        """Administrator control center with high-level metrics, ledger status, and audit snippets."""
        conn = get_db_connection(app.config["DATABASE_PATH"])
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS count FROM patients;")
            total_patients = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) AS count FROM doctors;")
            total_doctors = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) AS count FROM medical_records;")
            total_records = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) AS count FROM blockchain_blocks;")
            total_blocks = cursor.fetchone()["count"]

            cursor.execute("SELECT * FROM blockchain_blocks ORDER BY block_index DESC LIMIT 5;")
            recent_blocks = [dict(b) for b in cursor.fetchall()]

            recent_logs = get_audit_logs(app.config["DATABASE_PATH"], limit=5)

            return render_template(
                "admin_dashboard.html",
                active_page="dashboard",
                total_patients=total_patients,
                total_doctors=total_doctors,
                total_records=total_records,
                total_blocks=total_blocks,
                recent_blocks=recent_blocks,
                recent_logs=recent_logs
            )
        finally:
            conn.close()

    @app.route("/doctor/dashboard")
    @roles_required("doctor")
    def doctor_dashboard():
        """Doctor portal showing assigned/authored records and quick clinical tools."""
        doctor_id = session.get("doctor_id")
        if not doctor_id:
            # Query if not yet set in session
            doc_profile = get_doctor_by_user_id(session["user_id"], app.config["DATABASE_PATH"])
            if doc_profile:
                session["doctor_id"] = doc_profile["id"]
                session["doctor_code"] = doc_profile["doctor_code"]
                session["specialization"] = doc_profile["specialization"]
                doctor_id = doc_profile["id"]

        my_records = get_records_for_doctor(doctor_id, app.config["DATABASE_PATH"]) if doctor_id else []
        patients = get_all_patients(app.config["DATABASE_PATH"])

        return render_template(
            "doctor_dashboard.html",
            active_page="dashboard",
            my_records=my_records,
            total_patients=len(patients)
        )

    @app.route("/patient/dashboard")
    @roles_required("patient")
    def patient_dashboard():
        """Patient personal health portal: strictly locked to viewing own records."""
        user_id = session.get("user_id")
        patient_profile = get_patient_by_user_id(user_id, app.config["DATABASE_PATH"])
        if not patient_profile:
            flash("Patient record profile not found for this account.", "danger")
            return redirect(url_for("logout"))

        session["patient_id"] = patient_profile["id"]
        session["patient_code"] = patient_profile["patient_code"]

        records = get_records_for_patient(patient_profile["id"], app.config["DATABASE_PATH"])
        # Verify integrity for each of the patient's records
        records_with_status = []
        for r in records:
            ver_stat = verify_medical_record_integrity(r["id"], app.config["DATABASE_PATH"])
            records_with_status.append({"record": r, "status": ver_stat})

        return render_template(
            "patient_dashboard.html",
            active_page="dashboard",
            profile=patient_profile,
            records_with_status=records_with_status
        )

    # -------------------------------------------------------------
    # Patients Directory & Detail
    # -------------------------------------------------------------

    @app.route("/patients")
    @roles_required("admin", "doctor")
    def list_patients():
        """Displays patient directory for clinical staff and administration."""
        patients = get_all_patients(app.config["DATABASE_PATH"])
        return render_template("patients.html", active_page="patients", patients=patients)

    @app.route("/patients/<int:patient_id>")
    @login_required
    def view_patient_detail(patient_id):
        """Displays patient profile and complete medical history with server-side authorization."""
        role = session.get("role")
        # Enforce server-side security: patient can only view themselves
        if role == "patient" and session.get("patient_id") != patient_id:
            conn = get_db_connection(app.config["DATABASE_PATH"])
            try:
                record_audit_event(
                    cursor_or_conn=conn,
                    action="UNAUTHORIZED_ACCESS_ATTEMPT",
                    entity_type="PATIENT",
                    entity_id=str(patient_id),
                    ip_address=get_client_ip(),
                    details=f"Patient user #{session.get('user_id')} attempted to access Patient #{patient_id}.",
                    actor_user_id=session.get("user_id")
                )
            finally:
                conn.close()
            return render_template("access_denied.html", current_role=role), 403

        patient = get_patient_by_id(patient_id, app.config["DATABASE_PATH"])
        if not patient:
            abort(404)

        records = get_records_for_patient(patient_id, app.config["DATABASE_PATH"])
        return render_template("patient_detail.html", active_page="patients", patient=patient, records=records)

    # -------------------------------------------------------------
    # Medical Records Management
    # -------------------------------------------------------------

    @app.route("/records")
    @roles_required("admin", "doctor")
    def list_records():
        """Lists medical records with versioning indicators."""
        records = get_all_records(app.config["DATABASE_PATH"])
        return render_template("records.html", active_page="records", records=records)

    @app.route("/records/create", methods=["GET", "POST"])
    @roles_required("doctor")
    def create_record_page():
        """Allows authenticated doctors to create a new medical record and anchor it to the blockchain."""
        doctor_id = session.get("doctor_id")
        if not doctor_id:
            doc = get_doctor_by_user_id(session["user_id"], app.config["DATABASE_PATH"])
            if doc:
                doctor_id = doc["id"]
                session["doctor_id"] = doc["id"]
            else:
                flash("Doctor profile not configured.", "danger")
                return redirect(url_for("dashboard"))

        if request.method == "POST":
            patient_id_raw = request.form.get("patient_id")
            record_type = request.form.get("record_type", "").strip()
            diagnosis = request.form.get("diagnosis", "").strip()
            prescription = request.form.get("prescription", "").strip()

            try:
                patient_id = int(patient_id_raw)
            except (ValueError, TypeError):
                flash("Please select a valid patient.", "danger")
                patients = get_all_patients(app.config["DATABASE_PATH"])
                return render_template("record_form.html", active_page="create_record", is_edit=False, patients=patients)

            success, err, rec_id = create_medical_record(
                patient_id=patient_id,
                doctor_id=doctor_id,
                doctor_user_id=session["user_id"],
                record_type=record_type,
                diagnosis=diagnosis,
                prescription=prescription,
                ip_address=get_client_ip(),
                db_path=app.config["DATABASE_PATH"]
            )

            if success:
                flash(f"Medical Record #{rec_id} (Version 1) created and anchored to the blockchain!", "success")
                return redirect(url_for("view_record_detail", record_id=rec_id))
            else:
                flash(err or "Failed to create medical record.", "danger")

        # GET request
        selected_patient_id = request.args.get("patient_id", type=int)
        patients = get_all_patients(app.config["DATABASE_PATH"])
        return render_template(
            "record_form.html",
            active_page="create_record",
            is_edit=False,
            patients=patients,
            selected_patient_id=selected_patient_id
        )

    @app.route("/records/<int:record_id>")
    @login_required
    def view_record_detail(record_id):
        """Displays record details, dual-phase cryptographic integrity status, and version timeline."""
        record = get_medical_record_by_id(record_id, app.config["DATABASE_PATH"])
        if not record:
            abort(404)

        # Server-side access restriction
        role = session.get("role")
        if role == "patient" and record["patient_id"] != session.get("patient_id"):
            conn = get_db_connection(app.config["DATABASE_PATH"])
            try:
                record_audit_event(
                    cursor_or_conn=conn,
                    action="UNAUTHORIZED_RECORD_ACCESS",
                    entity_type="MEDICAL_RECORD",
                    entity_id=str(record_id),
                    ip_address=get_client_ip(),
                    details=f"Patient #{session.get('patient_id')} attempted to view private record #{record_id}.",
                    actor_user_id=session.get("user_id")
                )
            finally:
                conn.close()
            return render_template("access_denied.html", current_role=role), 403

        versions = get_record_versions(record_id, app.config["DATABASE_PATH"])
        integrity = verify_medical_record_integrity(record_id, app.config["DATABASE_PATH"])

        return render_template(
            "record_detail.html",
            active_page="records",
            record=record,
            versions=versions,
            integrity=integrity
        )

    @app.route("/records/<int:record_id>/edit", methods=["GET", "POST"])
    @roles_required("doctor")
    def edit_record_page(record_id):
        """Allows doctors to update a medical record by creating an immutable new version and blockchain block."""
        doctor_id = session.get("doctor_id")
        if not doctor_id:
            doc = get_doctor_by_user_id(session["user_id"], app.config["DATABASE_PATH"])
            if doc:
                doctor_id = doc["id"]
                session["doctor_id"] = doc["id"]

        record = get_medical_record_by_id(record_id, app.config["DATABASE_PATH"])
        if not record:
            abort(404)

        if request.method == "POST":
            record_type = request.form.get("record_type", "").strip()
            diagnosis = request.form.get("diagnosis", "").strip()
            prescription = request.form.get("prescription", "").strip()

            success, err, new_ver = update_medical_record(
                record_id=record_id,
                doctor_id=doctor_id,
                doctor_user_id=session["user_id"],
                record_type=record_type,
                diagnosis=diagnosis,
                prescription=prescription,
                ip_address=get_client_ip(),
                db_path=app.config["DATABASE_PATH"]
            )

            if success:
                flash(f"Record #{record_id} successfully updated to Version {new_ver} and cryptographically anchored!", "success")
                return redirect(url_for("view_record_detail", record_id=record_id))
            else:
                flash(err or "Failed to update record.", "danger")

        return render_template(
            "record_form.html",
            active_page="records",
            is_edit=True,
            record=record
        )

    @app.route("/records/<int:record_id>/history")
    @login_required
    def view_record_history(record_id):
        """Displays chronological revision history comparing past snapshots against anchored blockchain blocks."""
        record = get_medical_record_by_id(record_id, app.config["DATABASE_PATH"])
        if not record:
            abort(404)

        role = session.get("role")
        if role == "patient" and record["patient_id"] != session.get("patient_id"):
            return render_template("access_denied.html", current_role=role), 403

        versions = get_record_versions(record_id, app.config["DATABASE_PATH"])
        return render_template("record_history.html", active_page="records", record=record, versions=versions)

    # -------------------------------------------------------------
    # Blockchain Ledger & Verification
    # -------------------------------------------------------------

    @app.route("/blockchain")
    @login_required
    def view_blockchain():
        """Displays the entire public SHA-256 hash ledger from Genesis to the latest block."""
        conn = get_db_connection(app.config["DATABASE_PATH"])
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM blockchain_blocks ORDER BY block_index ASC;")
            blocks = [dict(b) for b in cursor.fetchall()]
            return render_template("blockchain.html", active_page="blockchain", blocks=blocks)
        finally:
            conn.close()

    @app.route("/blockchain/verify", methods=["GET", "POST"])
    @login_required
    def verify_blockchain_page():
        """
        Executes dual-phase integrity verification:
        Checks hash continuity AND cross-verifies against actual database record snapshots.
        """
        conn = get_db_connection(app.config["DATABASE_PATH"])
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM blockchain_blocks ORDER BY block_index ASC;")
            blocks = [dict(b) for b in cursor.fetchall()]

            def fetcher(rid, ver):
                return fetch_record_version_for_blockchain(rid, ver, app.config["DATABASE_PATH"])

            result = verify_chain(blocks, fetcher)

            # Record audit event
            status_desc = "VERIFIED_VALID" if result["is_valid"] else "TAMPERING_DETECTED"
            record_audit_event(
                cursor_or_conn=conn,
                action="BLOCKCHAIN_AUDIT",
                entity_type="BLOCKCHAIN",
                entity_id=None,
                ip_address=get_client_ip(),
                details=f"Blockchain audit executed by {session.get('username')}: Result = {status_desc}.",
                actor_user_id=session.get("user_id")
            )

            return render_template("verification.html", active_page="verification", result=result)
        finally:
            conn.close()

    # -------------------------------------------------------------
    # Administration: Users & Tamper Simulation
    # -------------------------------------------------------------

    @app.route("/admin/users")
    @roles_required("admin")
    def list_users():
        """Lists registered system users and roles."""
        users = get_all_users(app.config["DATABASE_PATH"])
        return render_template("users.html", active_page="users", users=users)

    @app.route("/admin/users/create", methods=["GET", "POST"])
    @roles_required("admin")
    def create_user_page():
        """Allows administrators to register new users."""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            role = request.form.get("role", "patient").strip()
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip()

            success, err, new_id = register_user(
                username=username,
                password=password,
                role=role,
                full_name=full_name,
                email=email,
                actor_user_id=session.get("user_id"),
                ip_address=get_client_ip(),
                db_path=app.config["DATABASE_PATH"],
                doctor_code=request.form.get("doctor_code"),
                specialization=request.form.get("specialization"),
                license_number=request.form.get("license_number"),
                patient_code=request.form.get("patient_code"),
                date_of_birth=request.form.get("date_of_birth"),
                gender=request.form.get("gender"),
                blood_group=request.form.get("blood_group"),
                contact_phone=request.form.get("contact_phone"),
                address=request.form.get("address"),
                emergency_contact=request.form.get("emergency_contact")
            )
            if success:
                flash(f"New {role.capitalize()} account '{username}' ({full_name}) created successfully!", "success")
                if role == "patient":
                    return redirect(url_for("list_patients"))
                return redirect(url_for("list_users"))
            else:
                flash(err or "Failed to create user.", "danger")

        return render_template("user_form.html", active_page="users")

    @app.route("/admin/tamper-demo")
    @roles_required("admin")
    def tamper_demo_page():
        """College viva evaluation workbench for demonstrating live tamper detection."""
        return render_template("tamper_demo.html", active_page="tamper_demo")

    @app.route("/admin/tamper-demo/action", methods=["POST"])
    @roles_required("admin")
    def tamper_demo_action():
        """Executes controlled simulations of database tampering or recovery."""
        action_type = request.form.get("action_type")
        conn = get_db_connection(app.config["DATABASE_PATH"])

        try:
            with conn:
                cursor = conn.cursor()
                if action_type == "tamper_record":
                    # Intentionally alter the prescription in the SQLite database directly
                    cursor.execute("""
                        UPDATE medical_record_versions 
                        SET prescription = 'TAMPERED: Unauthorized Alteration of Prescription 1000mg IV'
                        WHERE record_id = 1 AND version_number = 1;
                    """)
                    record_audit_event(
                        cursor_or_conn=cursor,
                        action="SIMULATED_TAMPER_RECORD",
                        entity_type="MEDICAL_RECORD",
                        entity_id="1",
                        ip_address=get_client_ip(),
                        details="Simulated malicious direct SQL modification of Record #1 Version 1.",
                        actor_user_id=session.get("user_id")
                    )
                    flash("Simulated direct database tampering applied to Record #1 Version 1. Go to 'Integrity Audit' to see it flagged!", "warning")

                elif action_type == "tamper_block":
                    # Intentionally break the hash pointer of Block #2
                    cursor.execute("""
                        UPDATE blockchain_blocks 
                        SET previous_hash = 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'
                        WHERE block_index = 2;
                    """)
                    record_audit_event(
                        cursor_or_conn=cursor,
                        action="SIMULATED_TAMPER_BLOCK",
                        entity_type="BLOCKCHAIN",
                        entity_id="2",
                        ip_address=get_client_ip(),
                        details="Simulated malicious previous_hash mutation on Block #2.",
                        actor_user_id=session.get("user_id")
                    )
                    flash("Simulated broken hash pointer applied to Block #2. Cryptographic continuity broken!", "warning")

                elif action_type == "restore_all":
                    # Re-seed database to pristine authentic state
                    cursor.execute("DROP TABLE IF EXISTS audit_logs;")
                    cursor.execute("DROP TABLE IF EXISTS blockchain_blocks;")
                    cursor.execute("DROP TABLE IF EXISTS medical_record_versions;")
                    cursor.execute("DROP TABLE IF EXISTS medical_records;")
                    cursor.execute("DROP TABLE IF EXISTS doctors;")
                    cursor.execute("DROP TABLE IF EXISTS patients;")
                    cursor.execute("DROP TABLE IF EXISTS users;")
            
            # Recreate and seed after clean drop
            if action_type == "restore_all":
                init_db(app.config["DATABASE_PATH"])
                seed_demo_data(app.config["DATABASE_PATH"])
                flash("Database and Blockchain successfully restored to 100% verified authentic state!", "success")

            return redirect(url_for("tamper_demo_page"))
        finally:
            conn.close()

    @app.route("/audit-logs")
    @roles_required("admin")
    def view_audit_logs():
        """Displays complete audit log history for compliance review."""
        logs = get_audit_logs(app.config["DATABASE_PATH"], limit=200)
        return render_template("audit_logs.html", active_page="audit_logs", logs=logs)

    # -------------------------------------------------------------
    # Error Handlers
    # -------------------------------------------------------------

    @app.errorhandler(403)
    def forbidden_error(e):
        return render_template("access_denied.html", current_role=session.get("role")), 403

    @app.errorhandler(404)
    def not_found_error(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("500.html"), 500

    return app


# Application entry point
app = create_app()

if __name__ == "__main__":
    # Local development server on port 5000 as specified
    print("\n" + "=" * 65)
    print("  Healthcare Record Management System Using Blockchain Technology")
    print("  Development Server Running on Windows 11")
    print("  URL: http://127.0.0.1:5000/")
    print("  Demo Accounts: admin / Admin@123  |  dr_sharma / Doctor@123")
    print("=" * 65 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=True)
