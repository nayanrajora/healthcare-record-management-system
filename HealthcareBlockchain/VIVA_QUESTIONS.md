# VIVA_QUESTIONS.md
## Healthcare Record Management System Using Blockchain Technology
### Comprehensive College Viva & Technical Examination Guide (35 Questions & Answers)

This guide is designed for undergraduate Computer Science (B.Tech) viva-voce examinations, project reviews, and lab evaluations. The answers are written in clear, technically rigorous, yet beginner-friendly language.

---

### CATEGORY 1: PYTHON & FLASK ARCHITECTURE

#### Q1. What is Flask, and why did you choose it over Django or FastAPI for this project?
**Answer:** Flask is a lightweight Web Server Gateway Interface (WSGI) micro-framework for Python. It provides the core essentials (routing, request handling, Jinja2 templating, sessions) without forcing an inflexible project structure or heavy Object Relational Mappers (ORMs). For an educational blockchain project, Flask allows us to maintain direct control over SQLite transactions, custom cryptographic hashing functions, and raw parameterized SQL queries without framework magic obscuring our logic.

#### Q2. What is the role of `app.py`, and how does the application factory pattern work?
**Answer:** `app.py` is the central controller of our application. We implement an application factory function `create_app(config_class)` that initializes Flask, configures security keys, binds the CSRF protection extension, registers HTTP routes, and attaches global error handlers (403, 404, 500). This design decouples application initialization from execution, enabling our automated unit test suite to spin up isolated test instances with temporary databases without modifying production code.

#### Q3. How does Jinja2 templating work in this project, and how does template inheritance help?
**Answer:** Jinja2 is Flask's built-in templating engine that renders dynamic HTML on the server. We use template inheritance via `templates/base.html`, which defines the shared sidebar navigation, header, SVG icons, flash messages, and user profile badge. Child templates (such as `records.html` or `blockchain.html`) extend `base.html` and populate specific `{% block content %}` sections, ensuring strict code reusability (DRY - Don't Repeat Yourself).

#### Q4. How does Flask handle client sessions, and how are session cookies secured?
**Answer:** Flask uses cryptographically signed client-side cookies to store session state (such as `user_id` and `role`). The session cookie is signed using the server's `SECRET_KEY` via HMAC (Hash-based Message Authentication Code). To protect against common web vulnerabilities, we configure:
- `SESSION_COOKIE_HTTPONLY = True`: Blocks client-side JavaScript from accessing cookies (mitigating XSS session theft).
- `SESSION_COOKIE_SAMESITE = 'Lax'`: Mitigates Cross-Site Request Forgery (CSRF).
- `PERMANENT_SESSION_LIFETIME = 3600`: Sets session expiry to 1 hour.

#### Q5. Why is this project implemented purely with Vanilla HTML, CSS, and JavaScript rather than React?
**Answer:** Using Vanilla HTML5, CSS3, and JavaScript eliminates Node.js dependencies, npm build chains, node_modules bloat, and compilation steps. The project runs immediately on any standard Windows 11 laptop with only Python installed. It also ensures that the backend enforces all business logic, authorization checks, and data validation, rather than trusting client-side JavaScript state.

---

### CATEGORY 2: RELATIONAL DATABASE & SQLITE

#### Q6. What database is used, and why is SQLite appropriate for this college major project?
**Answer:** We use SQLite 3 via Python's built-in `sqlite3` standard library module. SQLite is a serverless, self-contained, transactional SQL database engine that stores the entire database in a single local disk file (`instance/healthcare.db`). It requires zero background services, no separate database server setup, and no connection credentials, making it completely portable and reliable for local academic evaluation.

#### Q7. Are foreign key constraints enabled by default in SQLite? How did you enforce them?
**Answer:** No. By default, SQLite disables foreign key enforcement for backward compatibility with SQLite 2. In our `database.py` module, every database connection executes `PRAGMA foreign_keys = ON;` immediately upon opening:
```python
conn = sqlite3.connect(path)
conn.execute("PRAGMA foreign_keys = ON;")
```
This guarantees that relational integrity (e.g., preventing a medical record from referencing a non-existent `patient_id` or `doctor_id`) is strictly enforced at the database engine level.

#### Q8. What database tables exist in this system, and what are their relationships?
**Answer:** The system contains 7 interconnected tables:
1. `users`: Stores authentication credentials, hashed passwords, roles (`admin`, `doctor`, `patient`), and active status.
2. `patients`: Stores patient demographics (DOB, blood group, emergency contact) linked to `users.id` (1-to-1).
3. `doctors`: Stores physician profiles (specialization, license number) linked to `users.id` (1-to-1).
4. `medical_records`: Stores active clinical records linking `patient_id` and `doctor_id` (1-to-Many).
5. `medical_record_versions`: Immutable history of every version snapshot (v1, v2, v3) of a medical record.
6. `blockchain_blocks`: The cryptographically linked hash ledger referencing record creation and update events.
7. `audit_logs`: Chronological security and compliance logs.

#### Q9. How do you prevent SQL Injection attacks?
**Answer:** We strictly use **parameterized queries** (placeholders `?`) across all SQL executions throughout the entire application:
```python
cursor.execute("SELECT * FROM users WHERE username = ?;", (username,))
```
User inputs are passed separately as tuple parameters to the SQLite engine, preventing user-supplied strings from being interpreted as SQL commands. String concatenation or format strings (e.g., `f"SELECT ... WHERE username = '{username}'"`) are never used.

#### Q10. What is an atomic database transaction, and why is it essential when adding medical records?
**Answer:** An atomic transaction adheres to the ACID (Atomicity, Consistency, Isolation, Durability) principle: all operations succeed together, or if any step fails, all operations roll back as if nothing happened.
When a doctor creates or updates a record:
1. The record is inserted/updated in `medical_records`.
2. The version snapshot is saved in `medical_record_versions`.
3. The cryptographic block is calculated and inserted into `blockchain_blocks`.
4. The audit log is recorded in `audit_logs`.
All four steps occur within a single `with conn:` transaction block. If the block creation or database write fails, SQLite rolls back the entire transaction, preventing "orphaned" records without blockchain anchors.

---

### CATEGORY 3: AUTHENTICATION, AUTHORIZATION & SECURITY

#### Q11. How are user passwords stored in the database?
**Answer:** Passwords are never stored in plaintext. We use Werkzeug's cryptographic hashing functions (`generate_password_hash` and `check_password_hash`), which implement modern key derivation algorithms (`scrypt` or salted `pbkdf2:sha256`) with unique random salt per user.

#### Q12. What is a cryptographic salt, and why is it needed?
**Answer:** A salt is a cryptographically secure random sequence of bytes generated per password before hashing. Even if two users choose the identical password (e.g. `Doctor@123`), their stored hashes will look completely different because of different salts. This defends against:
1. **Rainbow Table attacks:** Precomputed tables of hash-password pairs become useless.
2. **Dictionary attacks:** An attacker cannot test many passwords at once against a database dump.

#### Q13. How does Role-Based Access Control (RBAC) work in this project?
**Answer:** RBAC is enforced on the server using Python function decorators defined in `auth.py`:
- `@login_required`: Checks whether `session.get('user_id')` is set.
- `@roles_required('admin', 'doctor')`: Validates that the authenticated user's `session.get('role')` exists in the permitted list.
If a patient attempts to access an administrator route (such as `/admin/users`), the decorator catches the violation, generates an audit log, and renders an HTTP 403 Access Denied template. Client-side button hiding is only for user experience; the server always enforces security.

#### Q14. How do you prevent a patient from viewing another patient's medical records?
**Answer:** We enforce data-level authorization checks inside record and patient detail routes:
```python
if role == "patient" and record["patient_id"] != session.get("patient_id"):
    return render_template("access_denied.html"), 403
```
Even if a patient manually changes the URL in their browser from `/records/1` to `/records/2`, the server verifies the patient's authenticated `session['patient_id']` against `record.patient_id`. If they do not match, access is immediately blocked and logged as an unauthorized access attempt.

#### Q15. What is CSRF, and how is it mitigated in this application?
**Answer:** Cross-Site Request Forgery (CSRF) is an attack where a malicious website tricks a user's browser into executing unwanted actions on a trusted site where the user is currently authenticated. We mitigate CSRF using Flask-WTF's `CSRFProtect`. Every state-changing form (POST requests for logins, record additions, updates, tamper simulations) includes a hidden, cryptographically signed token:
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```
Flask validates this token on every POST submission; missing or mismatched tokens are rejected with HTTP 400 Bad Request.

#### Q16. Why do login failures return a generic error message?
**Answer:** If an application states "User does not exist" when an invalid username is submitted, an attacker can enumerate registered usernames. By displaying a generic message: `"Invalid username or password. Please try again."`, we prevent username enumeration.

---

### CATEGORY 4: BLOCKCHAIN ARCHITECTURE & INTEGRITY

#### Q17. What is a blockchain in the context of this project?
**Answer:** In this project, a blockchain is an educational, tamper-evident cryptographic hash chain implemented in Python (`blockchain.py`). Each "block" represents a ledger entry recording a clinical event (`GENESIS`, `RECORD_CREATE`, or `RECORD_UPDATE`). Each block contains the SHA-256 hash of the canonical medical record data and the cryptographic hash of the immediate previous block, creating an unbroken chain linking back to Block #0 (Genesis).

#### Q18. What is SHA-256, and what are its key mathematical properties?
**Answer:** SHA-256 (Secure Hash Algorithm 256-bit) is a cryptographic hash function published by the National Institute of Standards and Technology (NIST) as a FIPS standard. Key properties:
1. **Deterministic:** The exact same input always generates the exact same 64-character hexadecimal digest.
2. **Fixed Output Length:** Always produces a 256-bit (32-byte / 64-hex char) string regardless of input size.
3. **Pre-image Resistance (One-Way):** It is computationally infeasible to reverse a SHA-256 hash back to its input.
4. **Avalanche Effect:** Altering even a single character or punctuation mark in the input changes roughly 50% of the output bits completely.
5. **Collision Resistance:** It is mathematically improbable to find two different inputs that produce the identical hash.

#### Q19. What is canonical JSON serialization, and why is it critical for hashing?
**Answer:** Python dictionaries do not guarantee deterministic string representation when converted using default formatting. If key `"patient_id"` is printed before `"doctor_id"` in one place and after it in another, the resulting strings will be different, generating completely different SHA-256 digests even though the underlying data is identical!
To eliminate this, our `canonical_json_dumps()` helper uses:
```python
json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
```
This enforces alphabetical key ordering and eliminates whitespace variability, guaranteeing 100% deterministic cryptographic hashing across all systems.

#### Q20. What is the Genesis Block?
**Answer:** The Genesis Block is Block #0, the foundational block of the blockchain. Because it has no predecessor, its `previous_hash` is initialized to 64 zeros (`"0" * 64`), its `record_id` is `None`, and its `event_type` is `"GENESIS"`. Its block hash is computed over its header and acts as the cryptographic root of trust for all future blocks.

#### Q21. What data fields constitute a block in your blockchain?
**Answer:** Each block contains:
- `block_index`: Sequential integer (0, 1, 2, ...).
- `timestamp`: UTC ISO-8601 formatted timestamp string.
- `event_type`: "GENESIS", "RECORD_CREATE", or "RECORD_UPDATE".
- `record_id`: Foreign key reference to `medical_records.id` (or None for Genesis).
- `record_version`: Version number of the record referenced.
- `record_hash`: SHA-256 hash of the canonical record payload.
- `previous_hash`: SHA-256 hash of the immediate predecessor block.
- `block_hash`: SHA-256 hash calculated over all header fields combined.

#### Q22. Explain your Dual-Phase Integrity Verification algorithm.
**Answer:** Many simple blockchain tutorials only check block headers. Our system implements a comprehensive two-phase verification:
- **Phase 1 (Chain Continuity & Header Verification):**
  1. Validates that Block #0 is a valid Genesis block.
  2. Validates that block indexes increment sequentially ($i = i_{prev} + 1$).
  3. Validates that each block's `previous_hash` matches block $[i-1]$'s `block_hash`.
  4. Recalculates the SHA-256 block hash for each block to ensure block headers were not modified.
- **Phase 2 (Data Ground-Truth Verification):**
  For every block referencing a medical record, the verification engine queries SQLite for the actual stored record version snapshot, recomputes the canonical SHA-256 hash from the raw database fields (`diagnosis`, `prescription`, `patient_id`, etc.), and checks whether it matches `block.record_hash`.
  If an attacker modifies a prescription in the database directly, Phase 2 immediately detects it!

#### Q23. Why do you store record hashes on the blockchain rather than the full medical text?
**Answer:** Storing raw medical data directly inside blockchain blocks creates privacy and architectural issues:
1. **Confidentiality:** Blockchain ledgers are often inspected by administrators or auditors who may not be authorized to view private psychiatric notes or sensitive diagnoses.
2. **Efficiency:** Hashes are compact, fixed-size (64 characters) strings, keeping ledger indexing fast.
3. **Separation of Concerns:** The database stores rich searchable clinical records, while the blockchain acts as a lightweight, tamper-evident cryptographic fingerprint ledger.

---

### CATEGORY 5: RECORD VERSIONING & AUDIT TRAILS

#### Q24. How does medical record versioning work when a doctor updates a record?
**Answer:** When a doctor updates an existing medical record:
1. The primary record pointer in `medical_records` has its `current_version` incremented (e.g. from v1 to v2).
2. The previous version snapshot in `medical_record_versions` is left untouched.
3. A new row is inserted into `medical_record_versions` with `version_number = 2`, the revised clinical notes, and the authoring doctor ID.
4. A canonical SHA-256 hash is computed for version 2.
5. A new block with `event_type = 'RECORD_UPDATE'` is linked to the latest blockchain block.
This preserves an immutable chronological timeline of revisions.

#### Q25. What is the difference between the audit log and the blockchain ledger?
**Answer:**
- **Audit Log (`audit_logs`):** A compliance log that records operational events (who logged in, which user accessed which record, timestamps, and IP addresses). It records system behavior.
- **Blockchain Ledger (`blockchain_blocks`):** A cryptographically chained structure that records mathematical proofs of data integrity. Unlike standard audit logs, which could theoretically be altered in SQL without detection, blockchain blocks are mathematically chained via SHA-256 previous-hash pointers.

#### Q26. Why do audit logs avoid duplicating full medical notes?
**Answer:** In healthcare IT (e.g. HIPAA and GDPR standards), audit logs must adhere to data minimization. Storing sensitive medical notes inside audit logs creates unnecessary data redundancy and leaks private health information (PHI) to IT administrators who only need to audit system activity, not read clinical evaluations.

---

### CATEGORY 6: TAMPER DETECTION DEMONSTRATION & VIVA LAB

#### Q27. How does the Tamper Simulation Workbench work?
**Answer:** We built a dedicated administrative laboratory (`/admin/tamper-demo`) to demonstrate tamper detection live during evaluation:
1. **Simulation 1 (Database Tampering):** Executes a direct raw SQL update on `medical_record_versions` modifying the prescription of Record #1 from `"Amlodipine 5mg"` to `"Unauthorized Narcotic"`, bypassing application logic.
2. **Verification Trigger:** When the examiner clicks "Run Cryptographic Audit", the dual-phase verification engine recalculates the hash of the tampered database record, finds it does not match the block's `record_hash`, and displays a red tampering alert detailing the discrepancy.
3. **Simulation 2 (Ledger Link Tampering):** Modifies a `previous_hash` pointer in `blockchain_blocks`. Re-verification immediately catches the broken cryptographic link.
4. **Restoration:** Drops and re-seeds clean demo data, restoring the system to 100% verified status.

#### Q28. What is the avalanche effect in hashing, and how does your project demonstrate it?
**Answer:** The avalanche effect is a property where changing even a single character in the input causes a drastic, unpredictable change in the output hash. For example, changing `"Amlodipine 5mg"` to `"Amlodipine 6mg"` completely alters all 64 hexadecimal characters of the SHA-256 digest. This makes it impossible for an attacker to alter data slightly without causing an obvious mismatch.

---

### CATEGORY 7: SYSTEM LIMITATIONS & WHY NO AI

#### Q29. Why does this project NOT contain AI integration?
**Answer:** This project focuses deliberately on **deterministic data integrity, cryptographic audit trails, and role-based security**. AI models (such as LLMs or machine learning classifiers) are non-deterministic, can hallucinate, and require external cloud APIs or heavy GPU dependencies. In medical records management, legal compliance demands deterministic, mathematical proofs of who wrote what, when it was written, and proof that it has not been altered.

#### Q30. What are the security limitations of a local educational hash chain?
**Answer:** This implementation is an educational, centralized hash chain. Its main limitation is that it does not feature decentralized consensus (such as Proof-of-Work, Proof-of-Stake, or Raft consensus across independent nodes). If an attacker has full physical root access to the Windows operating system and SQLite database file, they could theoretically rewrite every record and recompute all SHA-256 block hashes from Block #0 to the end. In an enterprise system, this hash chain would be anchored to an immutable decentralized ledger or hardware security module (HSM).

#### Q31. What is the difference between centralized EMRs and this blockchain-backed EMR?
**Answer:** In a standard centralized EMR, an insider with database access can execute an SQL update and alter patient records silently without any error or detection. In our blockchain-backed EMR, any mutation in the database breaks the mathematical consistency between the stored data and the blockchain block, guaranteeing that tampering is immediately visible to auditors.

#### Q32. How can this educational prototype be scaled in future work?
**Answer:** Future enhancements could include:
1. Multi-node peer-to-peer synchronization using gRPC or WebSockets.
2. Implementation of a consensus algorithm (such as Raft or PBFT - Practical Byzantine Fault Tolerance).
3. Asymmetric digital signatures (ECDSA or RSA) allowing doctors to sign records using their private cryptographic keys.
4. Export of cryptographic verification receipts as signed PDF documents for patients.

---

### CATEGORY 8: TESTING & WINDOWS DEPLOYMENT

#### Q33. What testing framework did you use, and what is your test coverage?
**Answer:** We used Python's built-in `unittest` framework. The automated test suite contains **30 tests** across 5 test modules:
- `test_blockchain.py` (8 tests): Genesis block, deterministic hashing, link continuity, header tampering, ground-truth detection.
- `test_database.py` (4 tests): Table creation, foreign key enforcement, demo seeding, idempotency.
- `test_records.py` (4 tests): Atomic creation, versioning snapshots, verification, rollback.
- `test_auth.py` (5 tests): Password verification, session management, registration hashing.
- `test_permissions.py` (5 tests): RBAC route protection, patient-to-patient isolation.
- `test_verification.py` (4 tests): End-to-end audit pass, tamper detection, link break, and recovery.
All 30 tests execute in isolated temporary databases, leaving the demonstration database uncorrupted.

#### Q34. How do you execute the automated tests on Windows 11?
**Answer:** From the `HealthcareBlockchain` directory in PowerShell or Command Prompt:
```powershell
python -m unittest discover tests
```

#### Q35. How do you start the application locally?
**Answer:** Run:
```powershell
python app.py
```
Then navigate to `http://127.0.0.1:5000/` in Google Chrome, Microsoft Edge, or any modern web browser.
