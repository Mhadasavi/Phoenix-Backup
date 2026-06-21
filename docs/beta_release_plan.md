# Phoenix Backup v0.1 Beta: Release Plan
## Roles: Product Manager & Release Manager
## Document Version: 1.0.0
## Execution Context: 100% Offline (Local Client PC)

---

## 1. Beta Release Scope & Objectives

The primary objective of **Phoenix Backup v0.1 Beta** is to validate the core local backup pipeline, the Recovery Intelligence Engine, and the dynamic readiness scoring system in real-world scenarios on Windows host machines auditing local Android hardware via ADB.

### 1.1 Out of Scope for v0.1 Beta
*   Cloud upload sync engines (Google Drive, OneDrive, etc.).
*   Automatic restore engine (Target installation pipelines).
*   Dynamic plugin updates from remote catalogs.

---

## 2. Feature Freeze Criteria

Before branching the code for the Beta release, the codebase must satisfy the following strict feature freeze gates:

1.  **Orchestration Integration Complete:** The discovery, ADB scan, SQLite storage, and CSV/HTML report generation modules must be unified.
2.  **API Schema Lock:** The JSON schemas for device inventory payloads, application classification profiles, and report payloads must be frozen.
3.  **Test Coverage Thresholds:**
    *   Unit Test Coverage: $\ge 85\%$ across all Python modules.
    *   Integration / Orchestrator Success Rate: $100\%$ on mock hardware pools.
4.  **Security Gaps Closed:** Zero open High or Critical security findings from the Sprint 1 audit.

---

## 3. Release Checklist

| Step | Action Item | Responsible Party | Verification Method |
| :--- | :--- | :--- | :--- |
| **1** | **Code Freeze & Tagging** | Release Manager | Git tag versioned `v0.1.0-beta.1` created. |
| **2** | **SQLite Migration Check** | Lead Engineer | Verify fresh SQLite migrations apply without error on Windows 10 & 11 environments. |
| **3** | **Package Bundling** | DevOps Lead | Package application using `PyInstaller` with air-gapped binary components included (local `adb.exe` version `34.0.5`, static `app_rules.json`). |
| **4** | **Host Integrity Check** | Security Architect | Verify compiled `.exe` digital signatures and run local scanning to confirm zero antivirus false positives on Windows Defender. |
| **5** | **Documentation Check** | Product Manager | User setup guide, ADB driver installation instructions, and local privacy logs disclosures updated. |

---

## 4. Testing Checklist

The QA team must execute the following validations before declaring a Release Candidate (RC) ready for Beta users:

*   **TC-01: Windows Host Compatibility**
    *   *Verify:* Build executes successfully on Windows 10 Pro (x64) and Windows 11 Home (ARM64 & x64) without administrative privileges.
*   **TC-02: Android OS Range Checks**
    *   *Verify:* Auditing runs correctly against physical devices running Android 11 (API 30) up to Android 14 (API 34).
*   **TC-03: USB Connection Drop Recovery**
    *   *Verify:* If the USB cable is unplugged mid-scan, the desktop app handles `ConnectionAbortedError` gracefully without database corruption or UI lockups.
*   **TC-04: Extreme Package Inventories**
    *   *Verify:* Auditor processes a device with $> 500$ installed applications in under $30\text{ seconds}$ without memory leaks.
*   **TC-05: Rules Matching Performance**
    *   *Verify:* Rules evaluation (Tier 1) for 200 packages resolves in $< 200\text{ms}$.

---

## 5. User Acceptance Testing (UAT)

### 5.1 Recruitment Profile
*   **Cohort Size:** 50 participants.
*   **OS Distribution:** 30 Windows 11, 20 Windows 10 users.
*   **Device Profiles:** Minimum of 8 different Android OEMs represented (Samsung, Google, Motorola, Xiaomi, OnePlus, etc.).

### 5.2 UAT Test Scenarios
1.  **Setup & Discovery:** Connect the phone over USB, enable USB debugging, and verify the Phoenix desktop application detects the device model and serial number.
2.  **Scan Execution:** Trigger the audit scan. Verify core communication databases (Contacts, SMS, Call logs) are successfully read, stored in SQLite, and media storage sizes calculated.
3.  **Readiness Score Review:** Examine the generated score. Perform the manual instructions for a critical finding (e.g. export Google Authenticator), resolve the warning card in the UI, and verify the score updates dynamically.
4.  **Report Verification:** Export the HTML and PDF reports. Verify tables, checklists, and graphics render correctly.

---

## 6. Bug Triage & Severity Classifications

All issues reported during the Beta phase will be processed through the Triage Committee (Release Manager, QA Lead, Dev Lead) using the following severity definitions:

| Severity Level | Definition | Target Resolution Time | Exit Block |
| :--- | :--- | :--- | :--- |
| **P0: Blocker** | App crashes, data corruption, database locks, false positive security alerts, or complete recovery readiness scoring miscalculations. | $< 24\text{ hours}$ | **Yes** (Must be 0) |
| **P1: Critical** | Core scanning features fail for a specific Android OS version or OEM profile, or PDF generation fails. | $< 72\text{ hours}$ | **Yes** (Must be 0) |
| **P2: Medium** | UI display alignment errors, minor latency stutters during scoring recalcs, or minor spelling errors in recommendations. | Next scheduled Beta build | **No** (Max 5 open) |
| **P3: Low** | Cosmetic adjustments, color palette shifts, or log file verbosity adjustments. | Post-v0.1 General Availability | **No** (No limit) |

---

## 7. Metrics to Collect (100% Offline)

Because the system operates in an air-gapped offline environment, telemetry is collected using **local opt-in session export logs** that users can voluntarily submit:

*   **Friction Metrics:**
    *   `device_discovery_duration_ms`: Latency from USB insertion to device validation.
    *   `scoring_recalculation_latency_ms`: Time to update readiness score after resolving a checklist task.
*   **Failure Rates:**
    *   `adb_handshake_failure_count`: Frequency of ADB communication breakdowns.
    *   `database_read_corruptions`: Integrity failure counts of SQLite logs.
*   **Operational Metrics:**
    *   `average_apps_scanned`: Number of packages audited per device.
    *   `high_risk_app_density`: Ratio of classified high-risk apps to standard apps.

---

## 8. Success Criteria (Go/No-Go Gate)

To exit the Beta phase and release Phoenix Backup v0.1 to General Availability, the following criteria must be satisfied:

1.  **Zero Open P0 & P1 Bugs:** No blockers or critical execution bugs remain unresolved.
2.  **UAT Completion Rate:** $\ge 90\%$ of UAT participants successfully complete the backup scan and report generation scenarios.
3.  **Score Verification Rate:** 100% accuracy verified in mathematical Readiness Score calculations across all test scenarios.
4.  **Local Storage Integrity:** 100% verification that no database locks or SQLite corruptions occurred during the beta tests.
