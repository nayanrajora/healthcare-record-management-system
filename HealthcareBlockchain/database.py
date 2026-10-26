"""
database.py
===========
SQLite Database Connection, Schema Initialization, and Seeding Module.

Features:
- Enforces SQLite foreign keys via 'PRAGMA foreign_keys = ON;' on every connection.
- Row factory set to sqlite3.Row for dict-like access.
- Safe parameterization across all SQL operations.
- Initializes Genesis Block automatically if the blockchain table is empty.
- Provides seed data for demonstration accounts (Admin, Doctors, Patients).
"""

import sqlite3
import os
from pathlib import Path
from werkzeug.security import generate_password_hash
from config import Config
from blockchain import (
    create_genesis_block,
    create_new_block,
    canonical_record_payload,
    hash_record_payload
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'doctor', 'patient')),
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    patient_code TEXT UNIQUE NOT NULL,
    date_of_birth TEXT NOT NULL,
    gender TEXT NOT NULL,
    blood_group TEXT NOT NULL,
    contact_phone TEXT NOT NULL,
    address TEXT NOT NULL,
    emergency_contact TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    doctor_code TEXT UNIQUE NOT NULL,
    specialization TEXT NOT NULL,
    license_number TEXT NOT NULL,
    contact_phone TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS medical_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    doctor_id INTEGER NOT NULL,
    record_type TEXT NOT NULL,
    diagnosis TEXT NOT NULL,
    prescription TEXT NOT NULL,
    current_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctors (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS medical_record_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER NOT NULL,
    version_number INTEGER NOT NULL,
    record_type TEXT NOT NULL,
    diagnosis TEXT NOT NULL,
    prescription TEXT NOT NULL,
    doctor_id INTEGER NOT NULL,
    canonical_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (record_id) REFERENCES medical_records (id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctors (id) ON DELETE RESTRICT,
    UNIQUE(record_id, version_number)
);

CREATE TABLE IF NOT EXISTS blockchain_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_index INTEGER UNIQUE NOT NULL,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    record_id INTEGER,
    record_version INTEGER,
    record_hash TEXT NOT NULL,
    previous_hash TEXT NOT NULL,
    block_hash TEXT UNIQUE NOT NULL,
    FOREIGN KEY (record_id) REFERENCES medical_records (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_user_id INTEGER,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    ip_address TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    details TEXT NOT NULL,
    FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_records_patient ON medical_records(patient_id);
CREATE INDEX IF NOT EXISTS idx_records_doctor ON medical_records(doctor_id);
CREATE INDEX IF NOT EXISTS idx_versions_record ON medical_record_versions(record_id);
CREATE INDEX IF NOT EXISTS idx_blocks_index ON blockchain_blocks(block_index);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
"""


def get_db_connection(db_path: str = None) -> sqlite3.Connection:
    """
    Creates and returns a connection to the SQLite database.
    Enforces foreign key constraints and dictionary-like row access.
    """
    path = db_path if db_path is not None else Config.DATABASE_PATH
    
    # Ensure directory exists if path is a file path (not :memory:)
    if path != ':memory:':
        parent_dir = Path(path).parent
        parent_dir.mkdir(parents=True, exist_ok=True)
        
    conn = sqlite3.connect(path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str = None) -> None:
    """
    Executes schema creation and ensures the Genesis block is persisted.
    """
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.executescript(SCHEMA_SQL)
            
            # Check if genesis block exists
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS count FROM blockchain_blocks WHERE block_index = 0;")
            row = cursor.fetchone()
            if row["count"] == 0:
                genesis = create_genesis_block()
                cursor.execute("""
                    INSERT INTO blockchain_blocks (
                        block_index, timestamp, event_type, record_id, record_version,
                        record_hash, previous_hash, block_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    genesis["block_index"],
                    genesis["timestamp"],
                    genesis["event_type"],
                    genesis["record_id"],
                    genesis["record_version"],
                    genesis["record_hash"],
                    genesis["previous_hash"],
                    genesis["block_hash"]
                ))
                
                # Add audit log for genesis initialization
                cursor.execute("""
                    INSERT INTO audit_logs (
                        actor_user_id, action, entity_type, entity_id, ip_address, timestamp, details
                    ) VALUES (NULL, 'GENESIS_INITIALIZED', 'BLOCKCHAIN', '0', '127.0.0.1', ?, 'Genesis block initialized.')
                """, (genesis["timestamp"],))
    finally:
        conn.close()


def seed_demo_data(db_path: str = None) -> None:
    """
    Populates the database with realistic demonstration accounts and medical records.
    Safe to run repeatedly; checks existing users first.
    """
    init_db(db_path)
    conn = get_db_connection(db_path)
    
    try:
        with conn:
            cursor = conn.cursor()
            
            # Check if admin already exists
            cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            if cursor.fetchone():
                return  # Already seeded
                
            now_ts = "2026-03-01T08:00:00Z"
            
            # 1. Create Admin
            admin_pwd = generate_password_hash("Admin@123")
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, full_name, email, is_active, created_at)
                VALUES (?, ?, 'admin', 'System Administrator', 'admin@medsecure.local', 1, ?)
            """, ("admin", admin_pwd, now_ts))
            admin_id = cursor.lastrowid
            
            # 2. Create Doctors
            doc1_pwd = generate_password_hash("Doctor@123")
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, full_name, email, is_active, created_at)
                VALUES (?, ?, 'doctor', 'Dr. Ramesh Sharma, MD', 'dr.sharma@medsecure.local', 1, ?)
            """, ("dr_sharma", doc1_pwd, now_ts))
            doc1_user_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO doctors (user_id, doctor_code, specialization, license_number, contact_phone, created_at)
                VALUES (?, 'DOC-101', 'Cardiology & Internal Medicine', 'MCI-2012-88741', '+91-98765-43210', ?)
            """, (doc1_user_id, now_ts))
            doc1_id = cursor.lastrowid

            doc2_pwd = generate_password_hash("Doctor@123")
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, full_name, email, is_active, created_at)
                VALUES (?, ?, 'doctor', 'Dr. Priya Patel, MBBS', 'dr.patel@medsecure.local', 1, ?)
            """, ("dr_patel", doc2_pwd, now_ts))
            doc2_user_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO doctors (user_id, doctor_code, specialization, license_number, contact_phone, created_at)
                VALUES (?, 'DOC-102', 'General Medicine & Pulmonology', 'MCI-2016-54129', '+91-98765-43211', ?)
            """, (doc2_user_id, now_ts))
            doc2_id = cursor.lastrowid

            # 3. Create Patients
            pat1_pwd = generate_password_hash("Patient@123")
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, full_name, email, is_active, created_at)
                VALUES (?, ?, 'patient', 'Johnathan Doe', 'john.doe@email.local', 1, ?)
            """, ("john_doe", pat1_pwd, now_ts))
            pat1_user_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO patients (user_id, patient_code, date_of_birth, gender, blood_group, contact_phone, address, emergency_contact, created_at)
                VALUES (?, 'PAT-1001', '1985-04-12', 'Male', 'O+', '+91-91234-56789', '24 Baker St, New Delhi', 'Jane Doe (+91-91234-56788)', ?)
            """, (pat1_user_id, now_ts))
            pat1_id = cursor.lastrowid

            pat2_pwd = generate_password_hash("Patient@123")
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, full_name, email, is_active, created_at)
                VALUES (?, ?, 'patient', 'Sarah Smith', 'sarah.smith@email.local', 1, ?)
            """, ("sarah_smith", pat2_pwd, now_ts))
            pat2_user_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO patients (user_id, patient_code, date_of_birth, gender, blood_group, contact_phone, address, emergency_contact, created_at)
                VALUES (?, 'PAT-1002', '1992-09-23', 'Female', 'A+', '+91-92345-67890', '15 Rosewood Enclave, Mumbai', 'Robert Smith (+91-92345-67899)', ?)
            """, (pat2_user_id, now_ts))
            pat2_id = cursor.lastrowid

            pat3_pwd = generate_password_hash("Patient@123")
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, full_name, email, is_active, created_at)
                VALUES (?, ?, 'patient', 'Rajesh Kumar', 'rajesh.kumar@email.local', 1, ?)
            """, ("raj_kumar", pat3_pwd, now_ts))
            pat3_user_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO patients (user_id, patient_code, date_of_birth, gender, blood_group, contact_phone, address, emergency_contact, created_at)
                VALUES (?, 'PAT-1003', '1978-11-05', 'Male', 'B+', '+91-93456-78901', '78 Sector 14, Bengaluru', 'Sunita Kumar (+91-93456-78909)', ?)
            """, (pat3_user_id, now_ts))
            pat3_id = cursor.lastrowid

            # Helper for adding demo records with block linking
            def add_demo_record(
                patient_id: int,
                doctor_id: int,
                doctor_user_id: int,
                record_type: str,
                diagnosis: str,
                prescription: str,
                timestamp: str,
                existing_record_id: int = None
            ):
                # Fetch latest block for linking
                cursor.execute("SELECT * FROM blockchain_blocks ORDER BY block_index DESC LIMIT 1;")
                prev_block = dict(cursor.fetchone())
                
                if existing_record_id is None:
                    # Create new record (Version 1)
                    cursor.execute("""
                        INSERT INTO medical_records (patient_id, doctor_id, record_type, diagnosis, prescription, current_version, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                    """, (patient_id, doctor_id, record_type, diagnosis, prescription, timestamp, timestamp))
                    record_id = cursor.lastrowid
                    version = 1
                    event_type = "RECORD_CREATE"
                else:
                    record_id = existing_record_id
                    cursor.execute("SELECT current_version FROM medical_records WHERE id = ?", (record_id,))
                    curr_v = cursor.fetchone()["current_version"]
                    version = curr_v + 1
                    cursor.execute("""
                        UPDATE medical_records 
                        SET record_type = ?, diagnosis = ?, prescription = ?, doctor_id = ?, current_version = ?, updated_at = ?
                        WHERE id = ?
                    """, (record_type, diagnosis, prescription, doctor_id, version, timestamp, record_id))
                    event_type = "RECORD_UPDATE"

                # Canonical hash for this version
                payload = canonical_record_payload(
                    patient_id=patient_id,
                    doctor_id=doctor_id,
                    record_type=record_type,
                    diagnosis=diagnosis,
                    prescription=prescription,
                    record_version=version,
                    created_at=timestamp
                )
                rec_hash = hash_record_payload(payload)

                # Insert immutable snapshot in medical_record_versions
                cursor.execute("""
                    INSERT INTO medical_record_versions (
                        record_id, version_number, record_type, diagnosis, prescription, doctor_id, canonical_hash, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (record_id, version, record_type, diagnosis, prescription, doctor_id, rec_hash, timestamp))

                # Create and insert linked blockchain block
                block = create_new_block(
                    previous_block=prev_block,
                    event_type=event_type,
                    record_id=record_id,
                    record_version=version,
                    record_hash=rec_hash,
                    timestamp=timestamp
                )
                cursor.execute("""
                    INSERT INTO blockchain_blocks (
                        block_index, timestamp, event_type, record_id, record_version, record_hash, previous_hash, block_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    block["block_index"], block["timestamp"], block["event_type"],
                    block["record_id"], block["record_version"], block["record_hash"],
                    block["previous_hash"], block["block_hash"]
                ))

                # Add Audit Log
                cursor.execute("""
                    INSERT INTO audit_logs (
                        actor_user_id, action, entity_type, entity_id, ip_address, timestamp, details
                    ) VALUES (?, ?, 'MEDICAL_RECORD', ?, '127.0.0.1', ?, ?)
                """, (
                    doctor_user_id, event_type, str(record_id), timestamp,
                    f"{event_type} - Record #{record_id} Version {version} signed and anchored to Block #{block['block_index']}."
                ))
                return record_id

            # Seed Record 1: John Doe - Initial Consultation by Dr. Sharma (v1)
            rec1_id = add_demo_record(
                patient_id=pat1_id,
                doctor_id=doc1_id,
                doctor_user_id=doc1_user_id,
                record_type="Consultation",
                diagnosis="Stage 1 Essential Hypertension. Resting BP 145/95 mmHg.",
                prescription="Lifestyle modification: Low sodium DASH diet, regular aerobic exercise 30 min/day. Tablet Amlodipine 5mg OD morning.",
                timestamp="2026-03-05T10:15:00Z"
            )

            # Seed Record 1 Update: John Doe - Follow-up Consultation by Dr. Sharma (v2)
            add_demo_record(
                patient_id=pat1_id,
                doctor_id=doc1_id,
                doctor_user_id=doc1_user_id,
                record_type="Consultation",
                diagnosis="Essential Hypertension (Well Controlled). Resting BP 122/80 mmHg. Good compliance.",
                prescription="Continue Tablet Amlodipine 5mg OD. Advised quarterly BP review.",
                timestamp="2026-03-25T11:30:00Z",
                existing_record_id=rec1_id
            )

            # Seed Record 2: Sarah Smith - Allergy & Asthma Consultation by Dr. Patel (v1)
            add_demo_record(
                patient_id=pat2_id,
                doctor_id=doc2_id,
                doctor_user_id=doc2_user_id,
                record_type="Diagnosis",
                diagnosis="Moderate Persistent Allergic Bronchial Asthma with seasonal exacerbation.",
                prescription="Budesonide/Formoterol Turbuhaler (160/4.5 mcg) 2 puffs BID. Levocetirizine 5mg at bedtime as needed for allergic rhinitis.",
                timestamp="2026-03-12T14:00:00Z"
            )

            # Seed Record 3: Rajesh Kumar - Lab Investigation by Dr. Sharma (v1)
            add_demo_record(
                patient_id=pat3_id,
                doctor_id=doc1_id,
                doctor_user_id=doc1_user_id,
                record_type="Lab Result",
                diagnosis="Annual Comprehensive Metabolic Profile: Fasting Blood Sugar 104 mg/dL (Impaired Fasting Glucose), Serum Triglycerides 185 mg/dL.",
                prescription="Dietary carbohydrate restriction. Re-check Fasting Glucose and HbA1c in 3 months. Tablet Atorvastatin 10mg OD bedtime.",
                timestamp="2026-03-18T16:45:00Z"
            )

    finally:
        conn.close()
