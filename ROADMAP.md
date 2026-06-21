# Phoenix Backup Product Roadmap

This document outlines the development lifecycle phases, completed sprints, and future release goals for **Phoenix Backup**.

---

## Completed Phases

### Sprint 1: Core Host Infrastructure
*   [x] Establish Python repository and SQLite relational schema runner.
*   [x] Create the ADB wrapper and device discovery manager.
*   [x] Build the basic file crawler and backup job transaction tables.

### Sprint 2: Recovery Intelligence & Exporters
*   [x] Create the `UnknownAppClassifier` utilizing permission and keyword voting.
*   [x] Implement the `FindingsEngine` and `RecoveryRecommendationEngine` prioritizing tasks topologically.
*   [x] Program the Readiness Score formula and tablet dynamic redistribution.
*   [x] Generate print-optimized PDF Exporter and standalone HTML Exporters.
*   [x] Implement the `BackupComparisonEngine` to track readiness deltas across historical snapshots.

---

## Active & Upcoming Sprints

### Sprint 3: Android Companion App MVP (Current Goal)
*   [ ] Initialize the Gradle mobile agent codebase namespace (`com.phoenix.companion`).
*   [ ] Establish the Loopback Socket Server binding on `127.0.0.1:50051`.
*   [ ] Implement intent-based random handshake token authentication checks.
*   [ ] Write data extraction cursors for SMS, Contacts, and Call Logs with safe pagination.
*   [ ] Establish automated permission grants using `adb shell pm grant` scripts.

### Sprint 4: Desktop Interface & IPC Wiring
*   [ ] Wire React UI components to invoke the Python orchestrator engine.
*   [ ] Implement interactive override checkboxes, allowing users to watch readiness scores update in real-time.
*   [ ] Design the visual step-by-step Guided Setup wizard (providing developer USB debugging help prompts).

---

## Future Backlog (Post-v1.0 Releases)

*   **Cloud-Sync Verification:** Check active cloud backup timestamps (e.g. Google Cloud sync status) programmatically via API metadata.
*   **Encrypted Archive Backups:** Compress and encrypt extracted data folders using client-side password keys before local disk writes.
*   **Automated Restore Testing:** Boot target mock emulators dynamically to verify that exported backups restore successfully without user intervention.
