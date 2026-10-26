import unittest
import sqlite3
import tempfile
import os
from pathlib import Path
from database import init_db, seed_demo_data, get_db_connection


class TestDatabase(unittest.TestCase):
    """Automated tests for SQLite schema, foreign keys, transactions, and seed data."""

    def setUp(self):
        # Create an isolated temporary SQLite database file for testing
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self.temp_dir.name, "test_healthcare.db")

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_database_initialization(self):
        """Database initialization must create all 7 core tables and the Genesis block."""
        init_db(self.db_path)
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        # Check all tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]
        expected_tables = [
            "users", "patients", "doctors", "medical_records",
            "medical_record_versions", "blockchain_blocks", "audit_logs"
        ]
        for tbl in expected_tables:
            self.assertIn(tbl, tables, f"Expected table '{tbl}' was not created.")
            
        # Check Genesis block exists (Block #0)
        cursor.execute("SELECT * FROM blockchain_blocks WHERE block_index = 0;")
        genesis = cursor.fetchone()
        self.assertIsNotNone(genesis)
        self.assertEqual(genesis["event_type"], "GENESIS")
        self.assertEqual(genesis["previous_hash"], "0" * 64)
        conn.close()

    def test_foreign_key_enforcement(self):
        """Foreign key constraint violations must raise sqlite3.IntegrityError."""
        init_db(self.db_path)
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        # Attempt to insert a patient with non-existent user_id 9999
        with self.assertRaises(sqlite3.IntegrityError):
            with conn:
                cursor.execute("""
                    INSERT INTO patients (
                        user_id, patient_code, date_of_birth, gender, blood_group,
                        contact_phone, address, emergency_contact, created_at
                    ) VALUES (9999, 'PAT-TEST', '2000-01-01', 'Female', 'A+', '1234567890', 'Test St', 'Emergency', '2026-01-01T00:00:00Z')
                """)
        conn.close()

    def test_seed_demo_data(self):
        """seed_demo_data must populate admin, doctors, patients, records, and linked blocks."""
        seed_demo_data(self.db_path)
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()

        # Check users count (1 admin + 2 doctors + 3 patients = 6 users)
        cursor.execute("SELECT COUNT(*) AS count FROM users;")
        self.assertEqual(cursor.fetchone()["count"], 6)

        # Check doctors count
        cursor.execute("SELECT COUNT(*) AS count FROM doctors;")
        self.assertEqual(cursor.fetchone()["count"], 2)

        # Check patients count
        cursor.execute("SELECT COUNT(*) AS count FROM patients;")
        self.assertEqual(cursor.fetchone()["count"], 3)

        # Check medical records count (3 base records)
        cursor.execute("SELECT COUNT(*) AS count FROM medical_records;")
        self.assertEqual(cursor.fetchone()["count"], 3)

        # Check versions count (Record 1 has v1 and v2, Record 2 has v1, Record 3 has v1 = 4 total)
        cursor.execute("SELECT COUNT(*) AS count FROM medical_record_versions;")
        self.assertEqual(cursor.fetchone()["count"], 4)

        # Check blockchain blocks count (Genesis + 4 record events = 5 blocks)
        cursor.execute("SELECT COUNT(*) AS count FROM blockchain_blocks;")
        self.assertEqual(cursor.fetchone()["count"], 5)

        # Check that blocks are properly chained
        cursor.execute("SELECT * FROM blockchain_blocks ORDER BY block_index ASC;")
        blocks = cursor.fetchall()
        for i in range(1, len(blocks)):
            self.assertEqual(blocks[i]["previous_hash"], blocks[i - 1]["block_hash"])
            self.assertEqual(blocks[i]["block_index"], blocks[i - 1]["block_index"] + 1)

        conn.close()

    def test_idempotent_seeding(self):
        """Calling seed_demo_data multiple times must not create duplicate users or corrupted chains."""
        seed_demo_data(self.db_path)
        seed_demo_data(self.db_path)  # Second call should be a no-op
        
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM users WHERE username = 'admin';")
        self.assertEqual(cursor.fetchone()["count"], 1)
        conn.close()


if __name__ == "__main__":
    unittest.main()
