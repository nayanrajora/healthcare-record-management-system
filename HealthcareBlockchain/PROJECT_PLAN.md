# PROJECT_PLAN.md
## Healthcare Record Management System Using Blockchain Technology

### 1. Problem Statement
Traditional healthcare management systems store electronic medical records (EMRs) in centralized relational databases. While centralized architectures offer high query performance, they suffer from critical vulnerabilities:
- **Insider Tampering:** Privileged database administrators or compromised system credentials can alter medical diagnoses, treatment dates, or prescriptions directly in the database without leaving an immutable audit trail.
- **Accidental Corruption:** Application glitches or faulty database updates can silently mutate patient records without detection.
- **Lack of Cryptographic Verification:** Standard audit logs stored in mutable SQL tables can themselves be modified, truncated, or forged.

### 2. Project Objectives
This project develops an educational, tamper-evident **Healthcare Record Management System Using Blockchain Technology** for local demonstration and academic evaluation. The core goals are:
1. **Centralized Medical Record Management:** Manage fictional patient profiles, doctor records, and clinical entries (consultations, lab results, prescriptions).
2. **Cryptographic Hash Chaining:** Build a Python-based SHA-256 hash chain where every record creation or update generates an immutable block linked cryptographically to its predecessor.
3. **Data Ground-Truth Integrity Verification:** Verify the ledger not only by checking block header hash links, but by recalculating canonical record hashes from actual database records and comparing them to block hashes.
4. **Role-Based Access Control (RBAC):** Strict server-side access control for three distinct roles: Administrator, Doctor, and Patient.
5. **Record Versioning:** Preserve historical snapshots of updated records so that past clinical diagnoses remain verifiable against past blockchain events.
6. **Comprehensive Auditing:** Log every critical security action (logins, record writes, verification runs, access violations).
7. **Zero AI Overhead:** Pure algorithmic, cryptographic, and web engineering without external cloud dependencies, paid services, or AI integration.

---

### 3. System Architecture

```
+-----------------------------------------------------------------------------------+
|                                  USER BROWSER                                     |
|               HTML5 / CSS3 / Vanilla JavaScript (No React, Responsive)            |
+-----------------------------------------------------------------------------------+
                                        |  HTTP/HTTPS
                                        v
+-----------------------------------------------------------------------------------+
|                               FLASK WEB BACKEND                                   |
|  - Session-based Auth & Role Decorators (@roles_required)                        |
|  - CSRF Protection (Flask-WTF)                                                    |
|  - Input Validation & Server-Side Sanitization                                   |
|  - Error Handlers (403, 404, 500)                                                 |
+-----------------------------------------------------------------------------------+
       |                                   |                                |
       v                                   v                                v
+------------------+             +-------------------+            +-----------------+
|  RECORD SERVICE  |             | BLOCKCHAIN MODULE |            |  AUDIT SERVICE  |
| - Create Record  |             | - SHA-256 Hashes  |            | - Log Actions   |
| - Update Version |             | - Canonical JSON  |            | - Query Events  |
| - Snapshot State |             | - Verify Links    |            | - Security Trail|
+------------------+             +-------------------+            +-----------------+
       \                                   /                               /
        \_________________________________/_______________________________/
                                          |
                              ATOMIC DB TRANSACTIONS
                                          v
+-----------------------------------------------------------------------------------+
|                               SQLITE DATABASE                                     |
|  - users                     - medical_records                                    |
|  - patients                  - medical_record_versions (immutable snapshots)     |
|  - doctors                   - blockchain_blocks                                  |
|                              - audit_logs                                         |
+-----------------------------------------------------------------------------------+
```

---

### 4. Database Schema Design

#### `users`
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `username` (TEXT UNIQUE NOT NULL)
- `password_hash` (TEXT NOT NULL)
- `role` (TEXT NOT NULL: 'admin' | 'doctor' | 'patient')
- `full_name` (TEXT NOT NULL)
- `email` (TEXT UNIQUE NOT NULL)
- `is_active` (INTEGER DEFAULT 1)
- `created_at` (TEXT NOT NULL)

#### `patients`
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `user_id` (INTEGER UNIQUE NOT NULL, FK -> users.id)
- `patient_code` (TEXT UNIQUE NOT NULL, e.g. 'PAT-1001')
- `date_of_birth` (TEXT NOT NULL)
- `gender` (TEXT NOT NULL)
- `blood_group` (TEXT NOT NULL)
- `contact_phone` (TEXT NOT NULL)
- `address` (TEXT NOT NULL)
- `emergency_contact` (TEXT NOT NULL)
- `created_at` (TEXT NOT NULL)

#### `doctors`
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `user_id` (INTEGER UNIQUE NOT NULL, FK -> users.id)
- `doctor_code` (TEXT UNIQUE NOT NULL, e.g. 'DOC-101')
- `specialization` (TEXT NOT NULL)
- `license_number` (TEXT NOT NULL)
- `contact_phone` (TEXT NOT NULL)
- `created_at` (TEXT NOT NULL)

#### `medical_records`
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `patient_id` (INTEGER NOT NULL, FK -> patients.id)
- `doctor_id` (INTEGER NOT NULL, FK -> doctors.id)
- `record_type` (TEXT NOT NULL: 'Consultation' | 'Diagnosis' | 'Prescription' | 'Lab Result')
- `diagnosis` (TEXT NOT NULL)
- `prescription` (TEXT NOT NULL)
- `current_version` (INTEGER DEFAULT 1)
- `created_at` (TEXT NOT NULL)
- `updated_at` (TEXT NOT NULL)

#### `medical_record_versions`
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `record_id` (INTEGER NOT NULL, FK -> medical_records.id)
- `version_number` (INTEGER NOT NULL)
- `record_type` (TEXT NOT NULL)
- `diagnosis` (TEXT NOT NULL)
- `prescription` (TEXT NOT NULL)
- `doctor_id` (INTEGER NOT NULL, FK -> doctors.id)
- `canonical_hash` (TEXT NOT NULL)
- `created_at` (TEXT NOT NULL)
- UNIQUE(record_id, version_number)

#### `blockchain_blocks`
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `block_index` (INTEGER UNIQUE NOT NULL)
- `timestamp` (TEXT NOT NULL)
- `event_type` (TEXT NOT NULL: 'GENESIS' | 'RECORD_CREATE' | 'RECORD_UPDATE')
- `record_id` (INTEGER, FK -> medical_records.id NULLABLE)
- `record_version` (INTEGER NULLABLE)
- `record_hash` (TEXT NOT NULL)
- `previous_hash` (TEXT NOT NULL)
- `block_hash` (TEXT UNIQUE NOT NULL)

#### `audit_logs`
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `actor_user_id` (INTEGER NULLABLE, FK -> users.id)
- `action` (TEXT NOT NULL)
- `entity_type` (TEXT NOT NULL)
- `entity_id` (TEXT NULLABLE)
- `ip_address` (TEXT NOT NULL)
- `timestamp` (TEXT NOT NULL)
- `details` (TEXT NOT NULL)

---

### 5. Blockchain Specifications

1. **Genesis Block:**
   - Index: `0`
   - Timestamp: Fixed ISO string or initial genesis timestamp
   - Event Type: `GENESIS`
   - Record ID / Version: `None`
   - Record Hash: `64 zeros` (`"0" * 64`)
   - Previous Hash: `64 zeros` (`"0" * 64`)
   - Block Hash: Recomputed SHA-256 of Genesis block header

2. **Deterministic Serialization:**
   - Uses `json.dumps(dict, sort_keys=True, separators=(',', ':'))`
   - Canonical representation of medical records guarantees identical SHA-256 digests across any runtime.

3. **Dual-Layer Integrity Verification:**
   - **Layer 1 (Chain Continuity):** Checks that each block points to the previous block's SHA-256 hash and each block hash is valid.
   - **Layer 2 (Ground-Truth Verification):** For each block referencing a medical record, the system retrieves the actual record version snapshot from SQLite, serializes it canonically, computes its SHA-256 digest, and compares it to `block.record_hash`.
   - Any manual tampering of database records triggers an immediate integrity failure with the exact record ID and expected vs actual hash.

4. **Atomic Transactions:**
   - Record writes, version snapshot inserts, blockchain block appends, and audit log entries are executed within a single database transaction (`BEGIN IMMEDIATE` / `COMMIT`). If any step fails, the entire transaction rolls back.

---

### 6. Development Phases

- **Phase 1:** Environment setup, project plan, blockchain module, and blockchain unit tests.
- **Phase 2:** Database schema, connection management, seed data, and database integrity tests.
- **Phase 3:** Core services (record_service, audit_service, validators) and business logic tests.
- **Phase 4:** Authentication, role-based session authorization, CSRF protection, and security tests.
- **Phase 5:** Flask routing, responsive templates, healthcare theme CSS, and JavaScript interactions.
- **Phase 6:** Tamper simulation suite, end-to-end verification, demo accounts, and error handling.
- **Phase 7:** Comprehensive documentation (README.md, BUILD_STATUS.md, VIVA_QUESTIONS.md) and faculty demonstration guide.

---

### 7. Educational Limitation Disclosure
This project uses a centralized Python hash chain designed specifically for local educational demonstrations. While it mathematically models the cryptographic chaining and tamper-evident guarantees of blockchain technology, it does not implement decentralized Proof-of-Work / Proof-of-Stake consensus or peer-to-peer gossip protocols. An attacker with full write access to the underlying SQLite database file could theoretically recompute the entire hash chain from Genesis onward. This distinction is thoroughly documented and covered in the viva defense guide.
