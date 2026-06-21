# Engineering Roles Reference

This document catalogs the specific engineering roles assumed during the design, implementation, auditing, and integration phases of the Phoenix Backup Sprint 3 lifecycle. It defines the scope of responsibilities and when each role should be invoked based on the operation.

---

## Assumed Roles & Operations Mapping

### 1. Senior Android Engineer
* **Scope of Operation:** Android Companion Application Implementation.
* **When to Use:**
  * Creating or modifying companion app modules (Java-only codebase).
  * Configuring Gradle build scripts (Groovy/Kotlin DSL) and multi-module dependencies.
  * Declaring app component manifests, permissions (Contacts, SMS, Call logs), and hardware features in `AndroidManifest.xml`.
  * Implementing foreground services, notification channels, background execution locks, and local SQLite/ContentResolver query providers.
  * Writing JUnit tests to verify cursor pagination limits and system configuration JSON structures.

### 2. Principal Android Architect
* **Scope of Operation:** High-Level Audits, Quality Assurance, and Security Compliance.
* **When to Use:**
  * Reviewing generated Android code for strict compliance with Android 11+ (API 30+) requirements.
  * Auditing target security configurations (e.g., binding server sockets strictly to loopback interfaces vs. external interfaces).
  * Validating lifecycle correctness, potential memory leaks in cursor/socket closures, and foreground notification constraints.
  * Enumerating architectural defects and refactoring plans before code execution phases begin.

### 3. Principal Systems Engineer
* **Scope of Operation:** Integration Layer Design & Secure Communication Protocols.
* **When to Use:**
  * Designing the end-to-end integration topology (React UI ↔ Electron IPC ↔ Python Client ↔ ADB Forwarding ↔ Android Socket Server).
  * Drafting component schemas, data framing protocol specs (big-endian 4-byte length prefixes), and sequence diagrams.
  * Designing cryptographic handshake authentication routines (e.g., microsecond-stamped HMAC-SHA256 signatures).
  * Structuring integration pipelines, task-level dependencies, and creating end-to-end integration verification test matrices.

### 4. Principal Engineer
* **Scope of Operation:** System-Wide Debugging & Root-Cause Analysis.
* **When to Use:**
  * Troubleshooting cross-component failures (e.g., when the UI reports "Not Extracted" despite device connections).
  * Tracing data flows step-by-step through the entire pipeline: UI ➔ IPC ➔ Subprocesses ➔ Tunnels ➔ Companion Service ➔ Database Persistence ➔ Dashboard UI updates.
  * Identifying interface gaps between disparate platforms (such as Node.js native libraries/types and Python scripts).

### 5. Senior Engineering Manager
* **Scope of Operation:** Project Board Planning & Execution Strategy.
* **When to Use:**
  * Defining Sprint backlogs, prioritizing tasks, and estimating efforts using Story Points.
  * Drafting the project's Definition of Done (DoD) and structuring the risk registers (mitigations for battery managers, OOM crashes, port collisions, etc.).
  * Documenting project states and next steps for the engineering team.

### 6. Desktop Application Release Engineer
* **Scope of Operation:** Electron Application Packaging, Deployment, and Build Pipelines.
* **When to Use:**
  * Building production bundles of the desktop app using Webpack configurations.
  * Managing release configurations, dependencies (handling node native bindings like `better-sqlite3` during packing), and artifact output directories.
  * Writing documentation and release guides (e.g., `BUILD_ANDROID.md`) covering installation, ADB commands, troubleshooting, and APK deployment.

### 7. Database Engineer / DBA
* **Scope of Operation:** SQLite Schema Design, Migrations, and Transaction Optimization.
* **When to Use:**
  * Designing the host-side SQLite tables (`job_contacts`, `job_sms`, `job_call_logs`, `job_extraction_logs`).
  * Creating initialization scripts, indices, and setting foreign keys for cascade deletions.
  * Optimizing database write performance and transactional integrity inside `BackupImportService`.

### 8. UX/UI Frontend Developer
* **Scope of Operation:** React UI Interface Design and Layout.
* **When to Use:**
  * Adding interactive interface components, panels (KeyDerivation, AssessmentResults, Settings), and visual state machines (scan status, backup progress).
  * Designing live console terminal displays with autoscroll features, spinners, and responsive status alert banners.
  * Styling components matching the sleeker dark mode design rules (using CSS-in-JS or vanilla CSS).

### 9. QA / Test Automation Engineer
* **Scope of Operation:** Verification Testing and Mock Environment Validation.
* **When to Use:**
  * Writing unit tests for network communication layers (e.g., mock socket testing for `client.py` and authenticator validation).
  * Running the automated monorepo tests (`npm run test`) and interpreting test output reports.
  * Creating E2E execution tests for multi-partition databases.

### 10. Security Analyst / Engineer
* **Scope of Operation:** Handshake Replay Protection and Transport Auditing.
* **When to Use:**
  * Verifying cryptographically secure random token generation (e.g., 32-character tokens generated on host).
  * Confirming that connections close within 3 seconds upon authentication failure to prevent denial-of-service/probing attacks.
  * Auditing sequence number counters in the framing protocol to block message replay attacks.

### 11. Python Backend / Host Systems Engineer
* **Scope of Operation:** Host Backup Scripting, Socket Clients, and CLI Utilities.
* **When to Use:**
  * Implementing the Python TCP socket communications client (`client.py`) with frame wrapping and message hashing.
  * Developing the `BackupRunner` orchestrator logic managing hardware scans, paginated socket fetches, and database persistence.
  * Creating CLI entry scripts (`run_backup.py`) utilizing arguments, log handlers, and exit codes for Electron shell invocations.
  * Writing Python unit and mock tests (`test_client.py`, `test_backup_runner.py`) using `unittest`.
