import unittest
import tempfile
import os
from app import create_app
from config import TestConfig
from database import init_db, seed_demo_data


class TestVerification(unittest.TestCase):
    """Automated end-to-end tests for blockchain ledger integrity and tamper detection."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self.temp_dir.name, "test_verif.db")
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

    def login_admin(self):
        return self.client.post("/login", data={
            "username": "admin",
            "password": "Admin@123"
        }, follow_redirects=True)

    def test_clean_chain_verification_passes(self):
        """Pristine database and blockchain must pass dual-phase audit 100%."""
        self.login_admin()
        res = self.client.post("/blockchain/verify", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"100% Cryptographic Ledger & Record Integrity Verified", res.data)
        self.assertIn(b"AUDIT PASSED", res.data)

    def test_record_tamper_simulation_detected(self):
        """Altering a database record version must immediately be detected during audit."""
        self.login_admin()

        # 1. Trigger simulation action to tamper Record #1
        tamper_res = self.client.post("/admin/tamper-demo/action", data={
            "action_type": "tamper_record"
        }, follow_redirects=True)
        self.assertEqual(tamper_res.status_code, 200)

        # 2. Run verification
        verify_res = self.client.post("/blockchain/verify", follow_redirects=True)
        self.assertEqual(verify_res.status_code, 200)
        self.assertIn(b"AUDIT FAILED", verify_res.data)
        self.assertIn(b"CRITICAL TAMPERING DETECTED", verify_res.data)

    def test_block_link_tamper_simulation_detected(self):
        """Breaking a hash link pointer must immediately be detected as broken link."""
        self.login_admin()

        # 1. Break block #2 hash pointer
        tamper_res = self.client.post("/admin/tamper-demo/action", data={
            "action_type": "tamper_block"
        }, follow_redirects=True)
        self.assertEqual(tamper_res.status_code, 200)

        # 2. Run verification
        verify_res = self.client.post("/blockchain/verify", follow_redirects=True)
        self.assertEqual(verify_res.status_code, 200)
        self.assertIn(b"AUDIT FAILED", verify_res.data)
        self.assertIn(b"Broken cryptographic link at block #2", verify_res.data)

    def test_restoration_returns_chain_to_valid(self):
        """Restoration action must return tampered database back to 100% verified state."""
        self.login_admin()

        # Tamper first
        self.client.post("/admin/tamper-demo/action", data={"action_type": "tamper_record"}, follow_redirects=True)
        
        # Restore
        restore_res = self.client.post("/admin/tamper-demo/action", data={"action_type": "restore_all"}, follow_redirects=True)
        self.assertEqual(restore_res.status_code, 200)

        # Re-verify
        verify_res = self.client.post("/blockchain/verify", follow_redirects=True)
        self.assertEqual(verify_res.status_code, 200)
        self.assertIn(b"AUDIT PASSED", verify_res.data)


if __name__ == "__main__":
    unittest.main()
