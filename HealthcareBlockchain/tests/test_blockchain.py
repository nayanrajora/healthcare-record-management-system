import unittest
import copy
from blockchain import (
    create_genesis_block,
    create_new_block,
    calculate_block_hash,
    hash_record_payload,
    canonical_record_payload,
    verify_single_block_hash,
    verify_chain,
    GENESIS_INDEX,
    GENESIS_PREVIOUS_HASH
)


class TestBlockchain(unittest.TestCase):
    """Automated tests for SHA-256 blockchain hashing, linking, and tamper detection."""

    def setUp(self):
        self.genesis = create_genesis_block()
        
        # Sample canonical medical record payload
        self.rec1_payload = canonical_record_payload(
            patient_id=1,
            doctor_id=1,
            record_type="Consultation",
            diagnosis="Essential Hypertension (Mild)",
            prescription="Amlodipine 5mg once daily",
            record_version=1,
            created_at="2026-03-15T09:30:00Z"
        )
        self.rec1_hash = hash_record_payload(self.rec1_payload)
        
        # Sample block 1
        self.block1 = create_new_block(
            previous_block=self.genesis,
            event_type="RECORD_CREATE",
            record_id=1,
            record_version=1,
            record_hash=self.rec1_hash,
            timestamp="2026-03-15T09:30:00Z"
        )
        
        # Sample block 2 (update to record 1)
        self.rec2_payload = canonical_record_payload(
            patient_id=1,
            doctor_id=1,
            record_type="Consultation",
            diagnosis="Essential Hypertension (Controlled)",
            prescription="Amlodipine 5mg once daily, maintain low sodium diet",
            record_version=2,
            created_at="2026-04-10T14:15:00Z"
        )
        self.rec2_hash = hash_record_payload(self.rec2_payload)
        self.block2 = create_new_block(
            previous_block=self.block1,
            event_type="RECORD_UPDATE",
            record_id=1,
            record_version=2,
            record_hash=self.rec2_hash,
            timestamp="2026-04-10T14:15:00Z"
        )
        
        self.valid_chain = [self.genesis, self.block1, self.block2]
        
        # Mock database record fetcher
        self.mock_db = {
            (1, 1): self.rec1_payload,
            (1, 2): self.rec2_payload
        }

    def mock_record_fetcher(self, record_id: int, version: int):
        return self.mock_db.get((record_id, version))

    def test_genesis_block_creation(self):
        """Genesis block must have index 0, 64 zeros as previous hash, and valid block hash."""
        self.assertEqual(self.genesis["block_index"], GENESIS_INDEX)
        self.assertEqual(self.genesis["previous_hash"], GENESIS_PREVIOUS_HASH)
        self.assertEqual(self.genesis["event_type"], "GENESIS")
        self.assertTrue(verify_single_block_hash(self.genesis))

    def test_hash_determinism(self):
        """Identical record data serialized with different dict key orders must produce the exact same hash."""
        payload_a = {
            "created_at": "2026-01-01T10:00:00Z",
            "diagnosis": "Common Cold",
            "doctor_id": 1,
            "patient_id": 2,
            "prescription": "Paracetamol 500mg",
            "record_type": "Consultation",
            "record_version": 1
        }
        # Reverse/shuffled key order
        payload_b = {
            "record_version": 1,
            "record_type": "Consultation",
            "prescription": "Paracetamol 500mg",
            "patient_id": 2,
            "doctor_id": 1,
            "diagnosis": "Common Cold",
            "created_at": "2026-01-01T10:00:00Z"
        }
        hash_a = hash_record_payload(payload_a)
        hash_b = hash_record_payload(payload_b)
        self.assertEqual(hash_a, hash_b)

    def test_chain_links(self):
        """Each block's previous_hash must match the preceding block's hash."""
        self.assertEqual(self.block1["previous_hash"], self.genesis["block_hash"])
        self.assertEqual(self.block2["previous_hash"], self.block1["block_hash"])
        self.assertEqual(self.block1["block_index"], 1)
        self.assertEqual(self.block2["block_index"], 2)

    def test_valid_chain_verification(self):
        """An untampered chain should pass dual-phase verification completely."""
        res = verify_chain(self.valid_chain, self.mock_record_fetcher)
        self.assertTrue(res["is_valid"])
        self.assertEqual(len(res["errors"]), 0)
        self.assertEqual(res["total_blocks"], 3)
        self.assertEqual(res["total_records_checked"], 2)

    def test_tamper_block_hash(self):
        """Tampering with block header fields (e.g. record_hash) without altering block_hash must fail."""
        tampered_chain = copy.deepcopy(self.valid_chain)
        # Modify record hash inside block 1
        tampered_chain[1]["record_hash"] = "f" * 64
        
        res = verify_chain(tampered_chain, self.mock_record_fetcher)
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("hash recalculation failed" in err for err in res["errors"]))

    def test_tamper_previous_hash_link(self):
        """Tampering with previous_hash pointer breaks cryptographic continuity."""
        tampered_chain = copy.deepcopy(self.valid_chain)
        tampered_chain[2]["previous_hash"] = "e" * 64
        
        res = verify_chain(tampered_chain, self.mock_record_fetcher)
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("Broken cryptographic link" in err for err in res["errors"]))

    def test_missing_or_reordered_blocks(self):
        """Removing a block in the middle must be detected as an index sequence break."""
        broken_chain = [self.genesis, self.block2]  # Block 1 omitted
        res = verify_chain(broken_chain, self.mock_record_fetcher)
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("Block sequence break" in err or "Broken cryptographic link" in err for err in res["errors"]))

    def test_database_record_content_tampering_detection(self):
        """
        Critical test: If the block header is intact, but someone directly modified
        the medical prescription in the database, verify_chain must detect this!
        """
        tampered_mock_db = copy.deepcopy(self.mock_db)
        # Malicious insider changes prescription in database
        tampered_mock_db[(1, 1)]["prescription"] = "Forged unauthorized narcotic prescription"
        
        def tampered_fetcher(rid, ver):
            return tampered_mock_db.get((rid, ver))
            
        res = verify_chain(self.valid_chain, tampered_fetcher)
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("CRITICAL TAMPERING DETECTED" in err for err in res["errors"]))


if __name__ == "__main__":
    unittest.main()
