import unittest
import tempfile
import os
from app import create_app
from config import TestConfig
from database import init_db, seed_demo_data


class TestPermissions(unittest.TestCase):
    """Automated tests for role-based access control (RBAC) and route protection."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self.temp_dir.name, "test_perm.db")
        init_db(self.db_path)
        seed_demo_data(self.db_path)

        class CustomTestConfig(TestConfig):
            DATABASE_PATH = self.db_path

        self.app = create_app(CustomTestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def login(self, username, password):
        return self.client.post("/login", data={
            "username": username,
            "password": password
        }, follow_redirects=True)

    def test_anonymous_access_denied(self):
        """Unauthenticated requests to protected endpoints must redirect to login."""
        endpoints = [
            "/dashboard",
            "/admin/dashboard",
            "/doctor/dashboard",
            "/patient/dashboard",
            "/records",
            "/records/create",
            "/blockchain"
        ]
        for ep in endpoints:
            res = self.client.get(ep)
            self.assertEqual(res.status_code, 302)
            self.assertIn("/login", res.headers.get("Location", ""))

    def test_patient_cannot_view_admin_or_doctor_pages(self):
        """Patient role must be strictly forbidden from accessing admin and doctor pages."""
        self.login("john_doe", "Patient@123")

        # Admin page -> 403
        res = self.client.get("/admin/dashboard")
        self.assertEqual(res.status_code, 403)

        # Admin user list -> 403
        res = self.client.get("/admin/users")
        self.assertEqual(res.status_code, 403)

        # Doctor record creation -> 403
        res = self.client.get("/records/create")
        self.assertEqual(res.status_code, 403)

    def test_doctor_cannot_view_admin_pages(self):
        """Doctor role must be forbidden from accessing admin management pages."""
        self.login("dr_sharma", "Doctor@123")

        res = self.client.get("/admin/dashboard")
        self.assertEqual(res.status_code, 403)

        res = self.client.get("/admin/users")
        self.assertEqual(res.status_code, 403)

        res = self.client.get("/audit-logs")
        self.assertEqual(res.status_code, 403)

    def test_patient_cannot_view_other_patient_record(self):
        """
        Critical privacy check:
        Patient John Doe (ID 1) must be forbidden from viewing Sarah Smith's (Patient ID 2)
        medical record (Record #2).
        """
        self.login("john_doe", "Patient@123")

        # Record #2 belongs to patient #2 (Sarah Smith)
        res = self.client.get("/records/2")
        self.assertEqual(res.status_code, 403)

        # Patient profile #2 belongs to Sarah Smith
        res = self.client.get("/patients/2")
        self.assertEqual(res.status_code, 403)

    def test_patient_can_view_own_record(self):
        """Patient John Doe must be permitted to view his own medical record (#1)."""
        self.login("john_doe", "Patient@123")
        res = self.client.get("/records/1")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Medical Record #1", res.data)


if __name__ == "__main__":
    unittest.main()
