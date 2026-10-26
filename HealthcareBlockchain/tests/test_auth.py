import unittest
import tempfile
import os
from flask import Flask, session
from database import init_db, seed_demo_data
from auth import (
    authenticate_user,
    login_user,
    logout_user,
    register_user,
    is_authenticated
)


class TestAuth(unittest.TestCase):
    """Automated tests for user authentication, password hashing, and session state."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self.temp_dir.name, "test_auth.db")
        seed_demo_data(self.db_path)

        # Minimal Flask app for testing session context
        self.app = Flask(__name__)
        self.app.secret_key = "test-secret-key"

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_successful_authentication(self):
        """Valid credentials must return user dictionary."""
        user = authenticate_user("admin", "Admin@123", self.db_path)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "admin")
        self.assertEqual(user["role"], "admin")

    def test_failed_authentication_bad_password(self):
        """Invalid password must return None."""
        user = authenticate_user("admin", "WrongPassword!", self.db_path)
        self.assertIsNone(user)

    def test_failed_authentication_bad_username(self):
        """Non-existent username must return None."""
        user = authenticate_user("ghost_user", "Admin@123", self.db_path)
        self.assertIsNone(user)

    def test_login_and_logout_session(self):
        """login_user must populate session keys and logout_user must clear them."""
        with self.app.test_request_context():
            user = authenticate_user("dr_sharma", "Doctor@123", self.db_path)
            login_user(user, self.db_path)
            
            self.assertTrue(is_authenticated())
            self.assertEqual(session.get("username"), "dr_sharma")
            self.assertEqual(session.get("role"), "doctor")
            self.assertIsNotNone(session.get("doctor_id"))

            logout_user()
            self.assertFalse(is_authenticated())
            self.assertIsNone(session.get("username"))

    def test_register_user_hashes_password(self):
        """Registering a user must save a Werkzeug hashed password, never plaintext."""
        ok, err, uid = register_user(
            username="new_nurse",
            password="SecurePassword@2026",
            role="doctor",
            full_name="Nurse Practitioner Jane",
            email="jane.nurse@medsecure.local",
            db_path=self.db_path
        )
        self.assertTrue(ok)
        self.assertIsNone(err)
        
        # Verify authenticated with new password
        user = authenticate_user("new_nurse", "SecurePassword@2026", self.db_path)
        self.assertIsNotNone(user)
        self.assertNotEqual(user["password_hash"], "SecurePassword@2026")
        self.assertTrue(user["password_hash"].startswith("scrypt:") or user["password_hash"].startswith("pbkdf2:"))


if __name__ == "__main__":
    unittest.main()
