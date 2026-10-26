import unittest
import tempfile
import os
from database import init_db, seed_demo_data, get_db_connection
from record_service import (
    create_medical_record,
    update_medical_record,
    get_medical_record_by_id,
    get_record_versions,
    verify_medical_record_integrity,
    fetch_record_version_for_blockchain
)
from blockchain import verify_chain


class TestRecordService(unittest.TestCase):
    """Automated tests for record versioning, atomic blockchain anchoring, and integrity checks."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self.temp_dir.name, "test_records.db")
        # Initialize schema + seed standard demo users and initial records
        seed_demo_data(self.db_path)

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_create_record_atomic(self):
        """Creating a record must create record row, version 1 snapshot, block, and audit log."""
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        # Get patient 1 and doctor 1
        cursor.execute("SELECT id FROM patients LIMIT 1;")
        pat_id = cursor.fetchone()["id"]
        cursor.execute("SELECT id, user_id FROM doctors LIMIT 1;")
        doc_row = cursor.fetchone()
        doc_id = doc_row["id"]
        doc_uid = doc_row["user_id"]
        conn.close()

        success, err, rec_id = create_medical_record(
            patient_id=pat_id,
            doctor_id=doc_id,
            doctor_user_id=doc_uid,
            record_type="Prescription",
            diagnosis="Acute Bronchitis with productive cough",
            prescription="Amoxicillin 500mg TDS for 5 days. Guaifenesin syrup 10ml TDS.",
            ip_address="192.168.1.50",
            db_path=self.db_path
        )
        self.assertTrue(success)
        self.assertIsNone(err)
        self.assertIsNotNone(rec_id)

        # Verify database state
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()

        # 1. Primary record
        cursor.execute("SELECT * FROM medical_records WHERE id = ?;", (rec_id,))
        rec = cursor.fetchone()
        self.assertEqual(rec["current_version"], 1)
        self.assertEqual(rec["record_type"], "Prescription")

        # 2. Version 1 snapshot
        cursor.execute("SELECT * FROM medical_record_versions WHERE record_id = ? AND version_number = 1;", (rec_id,))
        ver = cursor.fetchone()
        self.assertIsNotNone(ver)
        self.assertTrue(len(ver["canonical_hash"]) == 64)

        # 3. Blockchain block
        cursor.execute("SELECT * FROM blockchain_blocks WHERE record_id = ? AND record_version = 1;", (rec_id,))
        blk = cursor.fetchone()
        self.assertIsNotNone(blk)
        self.assertEqual(blk["event_type"], "RECORD_CREATE")
        self.assertEqual(blk["record_hash"], ver["canonical_hash"])

        # 4. Audit Log
        cursor.execute("SELECT * FROM audit_logs WHERE entity_id = ? AND action = 'RECORD_CREATE';", (str(rec_id),))
        audit = cursor.fetchone()
        self.assertIsNotNone(audit)
        self.assertEqual(audit["actor_user_id"], doc_uid)
        conn.close()

    def test_update_record_versioning(self):
        """Updating a record must leave version 1 intact and create version 2 linked to new block."""
        # Record 1 was seeded with v1 and v2. Let's update it to v3.
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT doctor_id FROM medical_records WHERE id = 1;")
        doc_id = cursor.fetchone()["doctor_id"]
        cursor.execute("SELECT user_id FROM doctors WHERE id = ?;", (doc_id,))
        doc_uid = cursor.fetchone()["user_id"]
        conn.close()

        success, err, new_ver = update_medical_record(
            record_id=1,
            doctor_id=doc_id,
            doctor_user_id=doc_uid,
            record_type="Consultation",
            diagnosis="Essential Hypertension (Controlled on revised therapy).",
            prescription="Continue Amlodipine 5mg OD. Added Telmisartan 40mg OD.",
            ip_address="127.0.0.1",
            db_path=self.db_path
        )
        self.assertTrue(success)
        self.assertEqual(new_ver, 3)

        # Check version history
        versions = get_record_versions(1, self.db_path)
        self.assertEqual(len(versions), 3)  # v3, v2, v1
        self.assertEqual(versions[0]["version_number"], 3)
        self.assertEqual(versions[1]["version_number"], 2)
        self.assertEqual(versions[2]["version_number"], 1)

    def test_record_integrity_verification_untampered(self):
        """An untouched record must report is_valid = True for all versions."""
        integrity = verify_medical_record_integrity(1, self.db_path)
        self.assertTrue(integrity["is_valid"])
        for v in integrity["versions"]:
            self.assertTrue(v["is_valid"])
            self.assertTrue(v["snapshot_intact"])
            self.assertTrue(v["block_intact"])

    def test_record_integrity_verification_tampered(self):
        """If a database record version is illegally edited directly in SQL, verification must fail."""
        conn = get_db_connection(self.db_path)
        with conn:
            cursor = conn.cursor()
            # Malicious direct SQL update bypassing application logic
            cursor.execute("""
                UPDATE medical_record_versions 
                SET prescription = 'Tampered Illicit Medication 500mg'
                WHERE record_id = 1 AND version_number = 1;
            """)
        conn.close()

        # Check individual record verification
        integrity = verify_medical_record_integrity(1, self.db_path)
        self.assertFalse(integrity["is_valid"])
        v1_status = [v for v in integrity["versions"] if v["version_number"] == 1][0]
        self.assertFalse(v1_status["snapshot_intact"])
        self.assertFalse(v1_status["is_valid"])

        # Check overall blockchain verification using fetcher adapter
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM blockchain_blocks ORDER BY block_index ASC;")
        blocks = [dict(b) for b in cursor.fetchall()]
        conn.close()

        def fetcher(rid, ver):
            return fetch_record_version_for_blockchain(rid, ver, self.db_path)

        chain_res = verify_chain(blocks, fetcher)
        self.assertFalse(chain_res["is_valid"])
        self.assertTrue(any("CRITICAL TAMPERING DETECTED" in err for err in chain_res["errors"]))


if __name__ == "__main__":
    unittest.main()
