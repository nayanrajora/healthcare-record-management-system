"""
record_service.py
=================
Medical Record Management and Integrity Service.

Architecture:
- Atomically executes record creation/updates, version snapshotting, blockchain anchoring,
  and audit logging within SQLite transactions.
- Provides cryptographic verification of medical records against stored blockchain blocks.
- Enforces immutability: past versions in `medical_record_versions` are never overwritten.
"""

from typing import Dict, Any, List, Optional, Tuple
from database import get_db_connection
from blockchain import (
    canonical_record_payload,
    hash_record_payload,
    create_new_block,
    verify_single_block_hash,
    get_current_utc_timestamp
)
from audit_service import record_audit_event
from validators import validate_medical_record_input
from models import MedicalRecord


def create_medical_record(
    patient_id: int,
    doctor_id: int,
    doctor_user_id: int,
    record_type: str,
    diagnosis: str,
    prescription: str,
    ip_address: str = "127.0.0.1",
    db_path: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Atomically creates a new medical record, creates its version 1 snapshot,
    computes its SHA-256 canonical hash, anchors a new block to the blockchain,
    and writes an audit log.
    
    Returns:
        (success: bool, error_message: Optional[str], new_record_id: Optional[int])
    """
    # 1. Validate inputs
    is_valid, err_msg = validate_medical_record_input(record_type, diagnosis, prescription)
    if not is_valid:
        return False, err_msg, None

    conn = get_db_connection(db_path)
    now_ts = get_current_utc_timestamp()

    try:
        with conn:
            cursor = conn.cursor()

            # Ensure patient and doctor exist
            cursor.execute("SELECT id FROM patients WHERE id = ?;", (patient_id,))
            if not cursor.fetchone():
                return False, f"Patient with ID {patient_id} does not exist.", None

            cursor.execute("SELECT id FROM doctors WHERE id = ?;", (doctor_id,))
            if not cursor.fetchone():
                return False, f"Doctor with ID {doctor_id} does not exist.", None

            # 2. Insert primary record (Version 1)
            cursor.execute("""
                INSERT INTO medical_records (
                    patient_id, doctor_id, record_type, diagnosis, prescription,
                    current_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """, (patient_id, doctor_id, record_type.strip(), diagnosis.strip(), prescription.strip(), now_ts, now_ts))
            record_id = cursor.lastrowid

            # 3. Compute canonical hash for Version 1
            payload = canonical_record_payload(
                patient_id=patient_id,
                doctor_id=doctor_id,
                record_type=record_type,
                diagnosis=diagnosis,
                prescription=prescription,
                record_version=1,
                created_at=now_ts
            )
            rec_hash = hash_record_payload(payload)

            # 4. Insert immutable Version 1 snapshot
            cursor.execute("""
                INSERT INTO medical_record_versions (
                    record_id, version_number, record_type, diagnosis, prescription,
                    doctor_id, canonical_hash, created_at
                ) VALUES (?, 1, ?, ?, ?, ?, ?, ?)
            """, (record_id, record_type.strip(), diagnosis.strip(), prescription.strip(), doctor_id, rec_hash, now_ts))

            # 5. Fetch latest block for previous-hash linking
            cursor.execute("SELECT * FROM blockchain_blocks ORDER BY block_index DESC LIMIT 1;")
            prev_row = cursor.fetchone()
            if not prev_row:
                raise RuntimeError("Blockchain has no blocks. Genesis block must be initialized.")
            prev_block = dict(prev_row)

            # 6. Generate and insert new block
            new_block = create_new_block(
                previous_block=prev_block,
                event_type="RECORD_CREATE",
                record_id=record_id,
                record_version=1,
                record_hash=rec_hash,
                timestamp=now_ts
            )
            cursor.execute("""
                INSERT INTO blockchain_blocks (
                    block_index, timestamp, event_type, record_id, record_version,
                    record_hash, previous_hash, block_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_block["block_index"],
                new_block["timestamp"],
                new_block["event_type"],
                new_block["record_id"],
                new_block["record_version"],
                new_block["record_hash"],
                new_block["previous_hash"],
                new_block["block_hash"]
            ))

            # 7. Record Audit Log
            record_audit_event(
                cursor_or_conn=cursor,
                action="RECORD_CREATE",
                entity_type="MEDICAL_RECORD",
                entity_id=str(record_id),
                ip_address=ip_address,
                details=f"Created medical record #{record_id} (Version 1). Anchored to Block #{new_block['block_index']}.",
                actor_user_id=doctor_user_id,
                timestamp=now_ts
            )

            return True, None, record_id
    except Exception as e:
        return False, f"Failed to create medical record: {str(e)}", None
    finally:
        conn.close()


def update_medical_record(
    record_id: int,
    doctor_id: int,
    doctor_user_id: int,
    record_type: str,
    diagnosis: str,
    prescription: str,
    ip_address: str = "127.0.0.1",
    db_path: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Atomically updates a medical record by incrementing its version, storing an immutable snapshot,
    anchoring an update event block to the blockchain, and logging the audit event.
    
    Returns:
        (success: bool, error_message: Optional[str], new_version_number: Optional[int])
    """
    is_valid, err_msg = validate_medical_record_input(record_type, diagnosis, prescription)
    if not is_valid:
        return False, err_msg, None

    conn = get_db_connection(db_path)
    now_ts = get_current_utc_timestamp()

    try:
        with conn:
            cursor = conn.cursor()

            # Verify existing record
            cursor.execute("SELECT * FROM medical_records WHERE id = ?;", (record_id,))
            rec_row = cursor.fetchone()
            if not rec_row:
                return False, f"Medical Record #{record_id} not found.", None

            patient_id = rec_row["patient_id"]
            current_version = rec_row["current_version"]
            new_version = current_version + 1

            # 1. Update primary record pointer
            cursor.execute("""
                UPDATE medical_records
                SET record_type = ?, diagnosis = ?, prescription = ?, doctor_id = ?,
                    current_version = ?, updated_at = ?
                WHERE id = ?
            """, (record_type.strip(), diagnosis.strip(), prescription.strip(), doctor_id, new_version, now_ts, record_id))

            # 2. Compute canonical hash for new version
            payload = canonical_record_payload(
                patient_id=patient_id,
                doctor_id=doctor_id,
                record_type=record_type,
                diagnosis=diagnosis,
                prescription=prescription,
                record_version=new_version,
                created_at=now_ts
            )
            rec_hash = hash_record_payload(payload)

            # 3. Store new immutable snapshot
            cursor.execute("""
                INSERT INTO medical_record_versions (
                    record_id, version_number, record_type, diagnosis, prescription,
                    doctor_id, canonical_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (record_id, new_version, record_type.strip(), diagnosis.strip(), prescription.strip(), doctor_id, rec_hash, now_ts))

            # 4. Fetch latest block for linking
            cursor.execute("SELECT * FROM blockchain_blocks ORDER BY block_index DESC LIMIT 1;")
            prev_row = cursor.fetchone()
            if not prev_row:
                raise RuntimeError("Blockchain has no blocks. Genesis block must be initialized.")
            prev_block = dict(prev_row)

            # 5. Anchor block
            new_block = create_new_block(
                previous_block=prev_block,
                event_type="RECORD_UPDATE",
                record_id=record_id,
                record_version=new_version,
                record_hash=rec_hash,
                timestamp=now_ts
            )
            cursor.execute("""
                INSERT INTO blockchain_blocks (
                    block_index, timestamp, event_type, record_id, record_version,
                    record_hash, previous_hash, block_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_block["block_index"],
                new_block["timestamp"],
                new_block["event_type"],
                new_block["record_id"],
                new_block["record_version"],
                new_block["record_hash"],
                new_block["previous_hash"],
                new_block["block_hash"]
            ))

            # 6. Record Audit Log
            record_audit_event(
                cursor_or_conn=cursor,
                action="RECORD_UPDATE",
                entity_type="MEDICAL_RECORD",
                entity_id=str(record_id),
                ip_address=ip_address,
                details=f"Updated medical record #{record_id} to Version {new_version}. Anchored to Block #{new_block['block_index']}.",
                actor_user_id=doctor_user_id,
                timestamp=now_ts
            )

            return True, None, new_version
    except Exception as e:
        return False, f"Failed to update medical record: {str(e)}", None
    finally:
        conn.close()


def get_medical_record_by_id(record_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves full medical record details joined with patient and doctor metadata."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                r.id,
                r.patient_id,
                p.patient_code,
                u_p.full_name AS patient_name,
                p.date_of_birth,
                p.gender,
                p.blood_group,
                r.doctor_id,
                d.doctor_code,
                u_d.full_name AS doctor_name,
                d.specialization AS doctor_specialization,
                r.record_type,
                r.diagnosis,
                r.prescription,
                r.current_version,
                r.created_at,
                r.updated_at
            FROM medical_records r
            JOIN patients p ON r.patient_id = p.id
            JOIN users u_p ON p.user_id = u_p.id
            JOIN doctors d ON r.doctor_id = d.id
            JOIN users u_d ON d.user_id = u_d.id
            WHERE r.id = ?;
        """, (record_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_record_versions(record_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all version snapshots for a medical record in descending order."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                v.id,
                v.record_id,
                v.version_number,
                v.record_type,
                v.diagnosis,
                v.prescription,
                v.doctor_id,
                u_d.full_name AS doctor_name,
                v.canonical_hash,
                v.created_at,
                b.block_index,
                b.block_hash
            FROM medical_record_versions v
            JOIN doctors d ON v.doctor_id = d.id
            JOIN users u_d ON d.user_id = u_d.id
            LEFT JOIN blockchain_blocks b ON b.record_id = v.record_id AND b.record_version = v.version_number
            WHERE v.record_id = ?
            ORDER BY v.version_number DESC;
        """, (record_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_records_for_patient(patient_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all medical records for a specific patient."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                r.id,
                r.patient_id,
                p.patient_code,
                u_p.full_name AS patient_name,
                r.doctor_id,
                u_d.full_name AS doctor_name,
                r.record_type,
                r.diagnosis,
                r.prescription,
                r.current_version,
                r.created_at,
                r.updated_at
            FROM medical_records r
            JOIN patients p ON r.patient_id = p.id
            JOIN users u_p ON p.user_id = u_p.id
            JOIN doctors d ON r.doctor_id = d.id
            JOIN users u_d ON d.user_id = u_d.id
            WHERE r.patient_id = ?
            ORDER BY r.updated_at DESC;
        """, (patient_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_records_for_doctor(doctor_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all medical records authored by a specific doctor."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                r.id,
                r.patient_id,
                p.patient_code,
                u_p.full_name AS patient_name,
                r.doctor_id,
                u_d.full_name AS doctor_name,
                r.record_type,
                r.diagnosis,
                r.prescription,
                r.current_version,
                r.created_at,
                r.updated_at
            FROM medical_records r
            JOIN patients p ON r.patient_id = p.id
            JOIN users u_p ON p.user_id = u_p.id
            JOIN doctors d ON r.doctor_id = d.id
            JOIN users u_d ON d.user_id = u_d.id
            WHERE r.doctor_id = ?
            ORDER BY r.updated_at DESC;
        """, (doctor_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_all_records(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all medical records for administrator view."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                r.id,
                r.patient_id,
                p.patient_code,
                u_p.full_name AS patient_name,
                r.doctor_id,
                u_d.full_name AS doctor_name,
                r.record_type,
                r.diagnosis,
                r.prescription,
                r.current_version,
                r.created_at,
                r.updated_at
            FROM medical_records r
            JOIN patients p ON r.patient_id = p.id
            JOIN users u_p ON p.user_id = u_p.id
            JOIN doctors d ON r.doctor_id = d.id
            JOIN users u_d ON d.user_id = u_d.id
            ORDER BY r.updated_at DESC;
        """, ())
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def verify_medical_record_integrity(record_id: int, db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Performs complete cryptographic verification of an individual medical record:
    1. Checks all historical versions against stored version snapshots.
    2. Recalculates canonical hash for each version.
    3. Cross-verifies each version against its anchored blockchain block.
    4. Detects any unauthorized modifications made directly to the database.
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medical_records WHERE id = ?;", (record_id,))
        rec = cursor.fetchone()
        if not rec:
            return {"is_valid": False, "error": f"Record #{record_id} does not exist.", "versions": []}

        patient_id = rec["patient_id"]
        cursor.execute("SELECT * FROM medical_record_versions WHERE record_id = ? ORDER BY version_number ASC;", (record_id,))
        versions = cursor.fetchall()

        all_valid = True
        version_results = []

        for v in versions:
            v_num = v["version_number"]
            v_payload = canonical_record_payload(
                patient_id=patient_id,
                doctor_id=v["doctor_id"],
                record_type=v["record_type"],
                diagnosis=v["diagnosis"],
                prescription=v["prescription"],
                record_version=v_num,
                created_at=v["created_at"]
            )
            recalculated_hash = hash_record_payload(v_payload)

            # Check snapshot hash
            snapshot_intact = (recalculated_hash == v["canonical_hash"])

            # Find matching blockchain block
            cursor.execute("""
                SELECT * FROM blockchain_blocks 
                WHERE record_id = ? AND record_version = ?;
            """, (record_id, v_num))
            block_row = cursor.fetchone()

            block_intact = False
            block_index = None
            if block_row:
                block_index = block_row["block_index"]
                block_dict = dict(block_row)
                block_hash_valid = verify_single_block_hash(block_dict)
                rec_hash_matches_block = (block_row["record_hash"] == recalculated_hash)
                block_intact = block_hash_valid and rec_hash_matches_block

            is_version_valid = snapshot_intact and block_intact
            if not is_version_valid:
                all_valid = False

            version_results.append({
                "version_number": v_num,
                "created_at": v["created_at"],
                "recalculated_hash": recalculated_hash,
                "stored_hash": v["canonical_hash"],
                "block_index": block_index,
                "snapshot_intact": snapshot_intact,
                "block_intact": block_intact,
                "is_valid": is_version_valid
            })

        return {
            "record_id": record_id,
            "current_version": rec["current_version"],
            "is_valid": all_valid,
            "versions": version_results
        }
    finally:
        conn.close()


def fetch_record_version_for_blockchain(record_id: int, version: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Adapter function passed to `blockchain.verify_chain`.
    Retrieves the actual record version data from SQLite to recompute ground-truth hash.
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                r.patient_id,
                v.doctor_id,
                v.record_type,
                v.diagnosis,
                v.prescription,
                v.version_number AS record_version,
                v.created_at
            FROM medical_record_versions v
            JOIN medical_records r ON v.record_id = r.id
            WHERE v.record_id = ? AND v.version_number = ?;
        """, (record_id, version))
        row = cursor.fetchone()
        if not row:
            return None
        return canonical_record_payload(
            patient_id=row["patient_id"],
            doctor_id=row["doctor_id"],
            record_type=row["record_type"],
            diagnosis=row["diagnosis"],
            prescription=row["prescription"],
            record_version=row["record_version"],
            created_at=row["created_at"]
        )
    finally:
        conn.close()
