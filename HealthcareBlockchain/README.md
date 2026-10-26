# Healthcare Record Management System Using Blockchain Technology

[![Python Version](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-Flask%203.x-green.svg)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/Database-SQLite%203-lightgrey.svg)](https://www.sqlite.org/)
[![Cryptography](https://img.shields.io/badge/Integrity-SHA--256%20Hash%20Chain-teal.svg)](https://en.wikipedia.org/wiki/SHA-2)
[![Tests](https://img.shields.io/badge/Tests-30%20Passed-success.svg)](file:///e:/Healthcare%20Record%20Management%20System/HealthcareBlockchain/tests)

> **College Major Project (B.Tech Computer Science & Engineering)**  
> A tamper-evident Electronic Medical Record (EMR) prototype featuring a Python-based SHA-256 cryptographic hash chain, medical record versioning, dual-phase ground-truth integrity verification, and strict role-based access control.

---

## 1. Project Overview & Objectives

In traditional centralized hospital information systems, clinical notes, lab investigations, and prescriptions reside in mutable relational databases. A malicious insider, compromised credential, or system glitch can silently alter patient treatment history without leaving a verifiable audit trail.

This application provides a **tamper-evident healthcare record management system**:
1. **Centralized Medical Management:** Manages fictional patient profiles, doctor entries, and medical consultations.
2. **Cryptographic Hash Chaining:** Every medical record creation or revision calculates a deterministic **SHA-256** hash of its canonical data and anchors a new block cryptographically linked to the preceding block.
3. **Dual-Phase Ground-Truth Verification:** Unlike naive blockchain tutorials that only verify stored block headers, this engine dynamically re-queries the actual SQLite database, recalculates the SHA-256 digest from raw fields, and cross-checks it against the anchored block to detect direct database tampering instantly.
4. **Medical Record Versioning:** Preserves historical snapshots ($v_1, v_2, v_3$) so that past clinical diagnoses remain verifiable against past blockchain events.
5. **Role-Based Access Control (RBAC):** Strict server-side authorization for **Administrator**, **Doctor**, and **Patient** roles.
6. **Zero AI Integration:** Built purely on deterministic algorithms, cryptographic hashing, and clean web engineering—no external AI services, machine learning models, or cloud dependencies.

---

## 2. Technology Stack

- **Backend:** Python 3.11+, Flask 3.1
- **Security & Cryptography:** Python standard `hashlib` (SHA-256), `werkzeug.security` (salted password hashing), `Flask-WTF` (CSRF protection)
- **Database:** SQLite 3 (Python built-in `sqlite3` module with foreign key enforcement)
- **Frontend:** HTML5, CSS3 (Modern Healthcare Teal/Slate design system), Vanilla JavaScript (No React, zero npm dependencies)
- **Automated Testing:** Python `unittest` framework (30 automated unit and integration tests)
- **Operating System:** Windows 11 (PowerShell & Command Prompt compatible)

---

## 3. Demonstration Credentials (Local Development)

All demo accounts are pre-seeded with realistic, **fictional** medical records for college evaluation:

| Role | Username | Password | Purpose / Features |
|---|---|---|---|
| **Administrator** | `admin` | `Admin@123` | System oversight, full blockchain ledger inspection, one-click integrity verification, audit log analysis, and interactive tamper simulation |
| **Doctor (Cardiology)** | `dr_sharma` | `Doctor@123` | Clinical authoring, patient record creation, version updating, and personal clinical history |
| **Doctor (General)** | `dr_patel` | `Doctor@123` | Consultations, lab investigations, and patient directory access |
| **Patient** | `john_doe` | `Patient@123` | Personal health portal: can only view his own medical history ($v_1, v_2$) and cryptographic verification badges |
| **Patient** | `sarah_smith` | `Patient@123` | Personal health portal: can only view her own medical records |

> [!NOTE]
> The login screen includes a **"College Demo Quick-Fill"** button group that auto-populates credentials in one click for quick viva demonstration!

---

## 4. Windows 11 Setup & Running Guide

### Step 1: Open PowerShell or Command Prompt
Open Windows Terminal, PowerShell, or Command Prompt:
```powershell
cd "E:\Healthcare Record Management System\HealthcareBlockchain"
```

### Step 2: Verify Python Version
```powershell
python --version
```
*(Requires Python 3.10 or higher. Python 3.11.0 is verified).*

### Step 3: Activate the Virtual Environment
- **In PowerShell:**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
  *If PowerShell displays an execution policy error, run:*
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  .\.venv\Scripts\Activate.ps1
  ```
- **In Command Prompt (CMD):**
  ```cmd
  .venv\Scripts\activate.bat
  ```

### Step 4: Verify or Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 5: Initialize the SQLite Database & Seed Data
*(This is already pre-initialized, but you can re-run it at any time safely):*
```powershell
python -c "import database; database.init_db(); database.seed_demo_data(); print('Database ready!')"
```

### Step 6: Run Automated Tests
```powershell
python -m unittest discover tests
```
*Expected output: `Ran 30 tests ... OK`*

### Step 7: Launch the Web Application
```powershell
python app.py
```

### Step 8: Open in Your Browser
Open your browser and navigate to:  
👉 **`http://127.0.0.1:5000/`**

---

## 5. College Viva Demonstration Script (Step-by-Step)

Follow this structured 5-minute walkthrough to demonstrate your project to faculty evaluators:

### Step 1: Login & Role-Based Access Control (1 min)
1. Navigate to `http://127.0.0.1:5000/login`.
2. Click **Patient John** quick-fill and log in:
   - Point out that John can **only** see his own records (Record #1).
   - Try manually entering `http://127.0.0.1:5000/records/2` (Sarah Smith's record) or `http://127.0.0.1:5000/admin/dashboard`.
   - Show the examiner the **403 Access Denied** page and explain that authorization is enforced on the server, not just hidden in the UI.
3. Sign out.

### Step 2: Doctor Clinical Authoring & Versioning (1.5 min)
1. Log in as **Dr. Sharma** (`dr_sharma` / `Doctor@123`).
2. Show the Doctor Dashboard:
   - Authored records count.
   - Click **Add Medical Record**: select a patient, select type (e.g. `Prescription`), enter diagnosis and treatment notes, and submit.
   - Point out the success banner: *"Record created and anchored to Block #N"*.
3. Open Record #1 and click **Update (Create Version 3)**:
   - Revise the dosage (e.g. add a medication) and submit.
   - Click **Version History**: show the visual timeline displaying $v_1, v_2, v_3$ side-by-side with their corresponding blockchain block hashes!
4. Sign out.

### Step 3: Blockchain Ledger Explorer & Cryptographic Audit (1.5 min)
1. Log in as **Admin** (`admin` / `Admin@123`).
2. Click **Ledger Explorer**:
   - Show Block #0 (Genesis Block) with `previous_hash = 000...000`.
   - Explain how Block #1's `previous_hash` matches Block #0's `block_hash`, Block #2 matches Block #1, and so on.
   - Point out that clicking any hash badge copies the full 64-character SHA-256 string to the clipboard.
3. Click **Integrity Audit**:
   - Show the examiner the **100% Cryptographic Ledger & Record Integrity Verified** green shield.
   - Explain: *"The engine didn't just check block headers; it dynamically retrieved the actual rows from SQLite and recalculated the SHA-256 hashes from the ground-truth database records."*

### Step 4: The "Killer" Viva Feature: Tamper Simulation Workbench (1 min)
1. Click **Tamper Simulation** from the sidebar or admin dashboard.
2. Click **Simulate Record Tampering**:
   - Explain to the examiner: *"We just executed a direct SQL UPDATE on Record #1's prescription in SQLite, simulating an insider attacker modifying a diagnosis or dosage without going through our software."*
3. Click **Check Verification Results**:
   - The screen immediately displays a prominent **RED ALERT: TAMPERING DETECTED!**
   - The report specifically identifies: *"Medical Record #1 (Version 1) in the database has been modified! Expected hash '...', but recalculated from database record is '...'."*
4. Return to **Tamper Simulation** and click **Restore Authentic Demo Data**:
   - Re-run the audit and show the green shield restored!

---

## 6. Project Architecture & Directory Structure

```
HealthcareBlockchain/
├── app.py                           # Application factory, routes & error handlers
├── config.py                        # Environment & testing configuration
├── database.py                      # SQLite connection, foreign keys & schema
├── models.py                        # Clean domain models (User, Patient, Doctor, Record, Block)
├── blockchain.py                    # SHA-256 hashing, block chaining, dual-phase audit
├── record_service.py                # Atomic record transactions, versioning & verification
├── audit_service.py                 # Security & compliance logging (privacy preserved)
├── validators.py                    # Server-side input validation & sanitization
├── auth.py                          # Werkzeug auth, session management & RBAC decorators
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment template
├── .gitignore                       # Git exclusions
├── PROJECT_PLAN.md                  # Comprehensive architectural design document
├── BUILD_STATUS.md                  # Detailed factual progress tracking
├── VIVA_QUESTIONS.md                # 35 viva questions & answers for student preparation
├── README.md                        # Master documentation
├── instance/
│   ├── .gitkeep
│   └── healthcare.db                # SQLite database with pre-seeded demo records
├── static/
│   ├── css/style.css                # Healthcare teal/slate responsive design system
│   └── js/main.js                   # UI interactivity, quick demo autofill, table filters
├── templates/                       # 15 Jinja2 templates (dashboards, records, blockchain, audit)
└── tests/                           # 30 automated unit & integration tests
    ├── test_blockchain.py           # 8 tests: hashing, linking, tampering, sequences
    ├── test_database.py             # 4 tests: schema, FK constraints, seeding, idempotency
    ├── test_records.py              # 4 tests: atomic writes, versioning snapshots, verification
    ├── test_auth.py                 # 5 tests: password hashing, session state, user registration
    ├── test_permissions.py          # 5 tests: RBAC decorators, patient-to-patient isolation
    └── test_verification.py         # 4 tests: end-to-end verification, tampering, restoration
```

---

## 7. Automated Test Suite

The project includes **30 automated tests** covering every layer:

```powershell
python -m unittest discover tests
```

### Test Coverage Breakdown:
| Test Module | Tests | Description |
|---|---|---|
| `tests/test_blockchain.py` | 8 | Genesis block, SHA-256 determinism, previous-hash linking, header tampering, sequence breaks, ground-truth tamper detection |
| `tests/test_database.py` | 4 | 7 core tables creation, foreign key enforcement, demo seeding, idempotent re-initialization |
| `tests/test_records.py` | 4 | Atomic record creation, version snapshots ($v_1 \to v_3$), untampered record validation, direct SQL tamper detection |
| `tests/test_auth.py` | 5 | Password verification, invalid credentials rejection, session login/logout, Werkzeug scrypt hashing |
| `tests/test_permissions.py` | 5 | Anonymous route protection, doctor/patient role boundaries, patient-to-patient private record isolation |
| `tests/test_verification.py` | 4 | Clean audit verification, simulated record tampering detection, broken hash link detection, state restoration |

*All tests execute against isolated temporary SQLite databases in memory or temporary directories, ensuring zero corruption to your demo data.*

---

## 8. Educational Limitations & Security Analysis

To score top marks in your viva, be prepared to discuss these design trade-offs:
1. **Centralized vs. Decentralized Blockchain:** This system implements an educational Python hash chain. It models the mathematical guarantees of SHA-256 linking and ground-truth verification. However, it does not feature a distributed peer-to-peer network with Proof-of-Work (PoW) or Byzantine Fault Tolerance (BFT). An attacker with root OS access to the SQLite file could theoretically recompute the entire chain from Genesis onward.
2. **Key Management:** In an enterprise hospital system, doctors would sign records using private asymmetric keys (e.g. ECDSA / RSA) stored on hardware cryptographic tokens. In this prototype, the server signs and anchors records on the doctor's behalf during an authenticated session.
3. **Audit Log Privacy:** Full medical descriptions are deliberately excluded from audit logs and blockchain blocks to comply with healthcare data minimization principles (HIPAA / GDPR).

---

## 9. Viva Preparation Checklist

Before entering your viva, ensure you can explain:
- [x] Why SHA-256 is deterministic and one-way (pre-image resistant).
- [x] What the **avalanche effect** is and how changing 1 character changes the entire hash.
- [x] Why canonical JSON serialization (sorted keys, compact separators) is mandatory for consistent hashes.
- [x] Why `PRAGMA foreign_keys = ON;` must be executed explicitly in SQLite.
- [x] How atomic transactions (`BEGIN IMMEDIATE` / `COMMIT`) prevent orphaned records.
- [x] Why passwords must be salted and hashed with algorithms like scrypt/pbkdf2 rather than raw MD5/SHA.
- [x] How `@roles_required` server decorators provide security that client-side CSS/JS cannot.
- [x] Why this project deliberately avoids AI integration (deterministic integrity vs. non-deterministic AI).
- [x] Review [VIVA_QUESTIONS.md](file:///e:/Healthcare%20Record%20Management%20System/HealthcareBlockchain/VIVA_QUESTIONS.md) for 35 detailed question-and-answer pairs!
