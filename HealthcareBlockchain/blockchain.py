"""
blockchain.py
=============
Python-based Educational Cryptographic Hash Chain for Medical Records.

Architecture:
- Utilizes SHA-256 cryptographic hashing (FIPS 180-4 standard).
- Guarantees deterministic serialization using canonical JSON (sorted keys, compact separators).
- Chains each block cryptographically via the previous block's SHA-256 hash.
- Implements two-phase verification:
    1. Chain Continuity Verification (checks sequential block indexes and previous-hash pointers).
    2. Data Ground-Truth Verification (recalculates record hashes against the actual database snapshots).

Academic Limitation Note:
This is an educational, centralized hash chain. It is not a decentralized peer-to-peer network
with Proof-of-Work or Byzantine Fault Tolerance consensus. It provides cryptographic tamper-evidence
against unauthorized record mutations in the database, but does not prevent an attacker with root
database access from rewriting the chain history from Genesis.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Callable

# Constants for Genesis Block
GENESIS_INDEX = 0
GENESIS_PREVIOUS_HASH = "0" * 64
GENESIS_RECORD_HASH = "0" * 64
GENESIS_TIMESTAMP = "2026-01-01T00:00:00Z"
GENESIS_EVENT_TYPE = "GENESIS"


def get_current_utc_timestamp() -> str:
    """Returns a deterministic ISO-8601 formatted UTC timestamp string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_json_dumps(data: Dict[str, Any]) -> str:
    """
    Serializes a Python dictionary to a canonical JSON string.
    Keys are strictly sorted, whitespace is minimized (separators (',', ':')),
    and values are encoded deterministically to ensure consistent SHA-256 digests.
    """
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def calculate_sha256(data_bytes: bytes) -> str:
    """Computes the hex digest of the SHA-256 hash for given bytes."""
    return hashlib.sha256(data_bytes).hexdigest()


def canonical_record_payload(
    patient_id: int,
    doctor_id: int,
    record_type: str,
    diagnosis: str,
    prescription: str,
    record_version: int,
    created_at: str
) -> Dict[str, Any]:
    """
    Constructs the canonical dictionary representation of a medical record version.
    This normalized structure is hashed to create the record's cryptographic fingerprint.
    """
    return {
        "created_at": str(created_at).strip(),
        "diagnosis": str(diagnosis).strip(),
        "doctor_id": int(doctor_id),
        "patient_id": int(patient_id),
        "prescription": str(prescription).strip(),
        "record_type": str(record_type).strip(),
        "record_version": int(record_version)
    }


def hash_record_payload(payload_dict: Dict[str, Any]) -> str:
    """Calculates the deterministic SHA-256 hash of a medical record's canonical payload."""
    canonical_str = canonical_json_dumps(payload_dict)
    return calculate_sha256(canonical_str.encode('utf-8'))


def calculate_block_hash(
    block_index: int,
    timestamp: str,
    event_type: str,
    record_id: Optional[int],
    record_version: Optional[int],
    record_hash: str,
    previous_hash: str
) -> str:
    """
    Computes the SHA-256 hash of a block header from its canonical JSON representation.
    """
    header_data = {
        "block_index": int(block_index),
        "event_type": str(event_type),
        "previous_hash": str(previous_hash),
        "record_hash": str(record_hash),
        "record_id": int(record_id) if record_id is not None else None,
        "record_version": int(record_version) if record_version is not None else None,
        "timestamp": str(timestamp)
    }
    canonical_header = canonical_json_dumps(header_data)
    return calculate_sha256(canonical_header.encode('utf-8'))


def create_genesis_block() -> Dict[str, Any]:
    """
    Constructs the initial Genesis Block (Block #0) for the ledger.
    """
    block_hash = calculate_block_hash(
        block_index=GENESIS_INDEX,
        timestamp=GENESIS_TIMESTAMP,
        event_type=GENESIS_EVENT_TYPE,
        record_id=None,
        record_version=None,
        record_hash=GENESIS_RECORD_HASH,
        previous_hash=GENESIS_PREVIOUS_HASH
    )
    return {
        "block_index": GENESIS_INDEX,
        "timestamp": GENESIS_TIMESTAMP,
        "event_type": GENESIS_EVENT_TYPE,
        "record_id": None,
        "record_version": None,
        "record_hash": GENESIS_RECORD_HASH,
        "previous_hash": GENESIS_PREVIOUS_HASH,
        "block_hash": block_hash
    }


def create_new_block(
    previous_block: Dict[str, Any],
    event_type: str,
    record_id: int,
    record_version: int,
    record_hash: str,
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a new cryptographic block linked to the preceding block in the chain.
    """
    if not previous_block:
        raise ValueError("Cannot create a new block without a valid previous block.")

    next_index = previous_block["block_index"] + 1
    ts = timestamp if timestamp else get_current_utc_timestamp()
    prev_hash = previous_block["block_hash"]

    block_hash = calculate_block_hash(
        block_index=next_index,
        timestamp=ts,
        event_type=event_type,
        record_id=record_id,
        record_version=record_version,
        record_hash=record_hash,
        previous_hash=prev_hash
    )

    return {
        "block_index": next_index,
        "timestamp": ts,
        "event_type": event_type,
        "record_id": record_id,
        "record_version": record_version,
        "record_hash": record_hash,
        "previous_hash": prev_hash,
        "block_hash": block_hash
    }


def verify_single_block_hash(block: Dict[str, Any]) -> bool:
    """
    Verifies that the stored block_hash matches the recalculated hash of its contents.
    """
    recalculated = calculate_block_hash(
        block_index=block["block_index"],
        timestamp=block["timestamp"],
        event_type=block["event_type"],
        record_id=block.get("record_id"),
        record_version=block.get("record_version"),
        record_hash=block["record_hash"],
        previous_hash=block["previous_hash"]
    )
    return recalculated == block["block_hash"]


def verify_chain(
    blocks: List[Dict[str, Any]], 
    record_version_fetcher: Optional[Callable[[int, int], Optional[Dict[str, Any]]]] = None
) -> Dict[str, Any]:
    """
    Performs comprehensive two-phase verification of the entire blockchain:
    
    Phase 1: Chain Integrity & Link Verification
      - Genesis block validation (index 0, previous_hash 64 zeros).
      - Strict sequential block index verification.
      - Previous-hash pointer matching (block[i].previous_hash == block[i-1].block_hash).
      - Recalculation of each block's cryptographic hash.
      
    Phase 2: Ground-Truth Medical Record Verification
      - For every block referencing a medical record (RECORD_CREATE / RECORD_UPDATE),
        fetches the actual database record version using `record_version_fetcher(record_id, record_version)`.
      - Recomputes the canonical record hash from actual database values.
      - Flags tampering if the database record content does not match the block's record_hash!
      
    Returns:
      A dictionary summarizing verification status, detailed block statuses, and any errors found.
    """
    result = {
        "is_valid": True,
        "total_blocks": len(blocks),
        "total_records_checked": 0,
        "errors": [],
        "verified_at": get_current_utc_timestamp(),
        "blocks_status": []
    }

    if not blocks:
        result["is_valid"] = False
        result["errors"].append("Blockchain ledger is completely empty. Genesis block is missing.")
        return result

    # 1. Verify Genesis Block
    genesis = blocks[0]
    genesis_status = {"block_index": 0, "event_type": genesis.get("event_type"), "status": "VALID", "details": "Genesis block verified."}

    if genesis.get("block_index") != GENESIS_INDEX:
        result["is_valid"] = False
        err = f"Genesis block index is {genesis.get('block_index')} instead of 0."
        result["errors"].append(err)
        genesis_status["status"] = "TAMPERED"
        genesis_status["details"] = err

    if genesis.get("previous_hash") != GENESIS_PREVIOUS_HASH:
        result["is_valid"] = False
        err = f"Genesis block previous_hash is invalid: '{genesis.get('previous_hash')}'."
        result["errors"].append(err)
        genesis_status["status"] = "TAMPERED"
        genesis_status["details"] = err

    if not verify_single_block_hash(genesis):
        result["is_valid"] = False
        err = "Genesis block hash recalculation failed. Genesis header contents were altered."
        result["errors"].append(err)
        genesis_status["status"] = "TAMPERED"
        genesis_status["details"] = err

    result["blocks_status"].append(genesis_status)

    # 2. Verify Subsequent Blocks
    for i in range(1, len(blocks)):
        curr = blocks[i]
        prev = blocks[i - 1]
        b_idx = curr.get("block_index")
        status_entry = {
            "block_index": b_idx,
            "event_type": curr.get("event_type"),
            "record_id": curr.get("record_id"),
            "record_version": curr.get("record_version"),
            "status": "VALID",
            "details": "Block integrity and link verified."
        }

        # Check sequential indexing
        expected_index = prev.get("block_index", -1) + 1
        if b_idx != expected_index:
            result["is_valid"] = False
            err = f"Block sequence break at block #{b_idx}: expected index #{expected_index}."
            result["errors"].append(err)
            status_entry["status"] = "TAMPERED"
            status_entry["details"] = err

        # Check previous hash pointer
        if curr.get("previous_hash") != prev.get("block_hash"):
            result["is_valid"] = False
            err = (
                f"Broken cryptographic link at block #{b_idx}: "
                f"previous_hash '{curr.get('previous_hash')[:12]}...' does not match "
                f"block #{prev.get('block_index')} hash '{prev.get('block_hash')[:12]}...'."
            )
            result["errors"].append(err)
            status_entry["status"] = "TAMPERED"
            status_entry["details"] = err

        # Check current block hash recalculation
        if not verify_single_block_hash(curr):
            result["is_valid"] = False
            err = f"Block #{b_idx} hash recalculation failed: header data has been tampered with."
            result["errors"].append(err)
            status_entry["status"] = "TAMPERED"
            status_entry["details"] = err

        # Check record content against actual database snapshot (Phase 2 verification)
        rec_id = curr.get("record_id")
        rec_ver = curr.get("record_version")
        if rec_id is not None and rec_ver is not None and record_version_fetcher is not None:
            result["total_records_checked"] += 1
            actual_record_data = record_version_fetcher(rec_id, rec_ver)
            if actual_record_data is None:
                result["is_valid"] = False
                err = f"Block #{b_idx} references Record #{rec_id} Version {rec_ver}, but it does not exist in the database."
                result["errors"].append(err)
                status_entry["status"] = "TAMPERED"
                status_entry["details"] = err
            else:
                recalculated_rec_hash = hash_record_payload(actual_record_data)
                if recalculated_rec_hash != curr.get("record_hash"):
                    result["is_valid"] = False
                    err = (
                        f"CRITICAL TAMPERING DETECTED: Medical Record #{rec_id} (Version {rec_ver}) "
                        f"in the database has been modified! Expected hash '{curr.get('record_hash')[:16]}...', "
                        f"but recalculated from database record is '{recalculated_rec_hash[:16]}...'."
                    )
                    result["errors"].append(err)
                    status_entry["status"] = "TAMPERED"
                    status_entry["details"] = err

        result["blocks_status"].append(status_entry)

    return result
