# MVP Orchestrator Module - Phoenix Backup

This module defines the **MVP Orchestration Flow** of the Phoenix Backup system. It acts as the pipeline controller that coordinates:
1.  **Device Discovery** (detects target connection details).
2.  **SQLite Persistence** (stores device records and updates backup jobs).
3.  **Application Audits** (lists packages and versions).
4.  **Reports Generation** (writes device metadata and application inventories to CSV files).

---

## 1. Sequence Diagram

```
+------------+          +--------------+          +----------------+          +--------------------+          +-------------+
|    Host    |          | Adb Wrapper  |          | Device Detector|          | Inventory Manager  |          | SQLite DB   |
| Orchestrator|          |  Interface   |          |    Service     |          |      Service       |          | Repository  |
+-----+------+          +------+-------+          +-------+--------+          +---------+----------+          +------+------+
      |                        |                          |                             |                        |
      | execute(serial)        |                          |                             |                        |
      |----------------------->|                          |                             |                        |
      |                        |                          |                             |                        |
      |                        | detect_devices()         |                             |                        |
      |------------------------+------------------------->|                             |                        |
      |                        |                          |                             |                        |
      |                        | get_device_property()    |                             |                        |
      |                        |<-------------------------|                             |                        |
      |                        |                          |                             |                        |
      |                        | stat -f -c /data         |                             |                        |
      |                        |<-------------------------|                             |                        |
      |                        |                          |                             |                        |
      |                        | Device Details JSON      |                             |                        |
      |                        |------------------------->|                             |                        |
      |                        |                          |                             |                        |
      |                        | AndroidDevice Object     |                             |                        |
      |                        |<-------------------------|                             |                        |
      |                        |                                                        |                        |
      | save_device() / create_job()                                                    |                        |
      |--------------------------------------------------------------------------------------------------------->|
      |                        |                                                        |                        |
      |                        | get_installed_apps()                                   |                        |
      |------------------------+-------------------------------------------------------->|                        |
      |                        |                                                        |                        |
      |                        | pm list packages -f -3                                 |                        |
      |                        |<-------------------------------------------------------|                        |
      |                        |                                                        |                        |
      |                        | pm dump <package>                                      |                        |
      |                        |<-------------------------------------------------------|                        |
      |                        |                                                        |                        |
      |                        | AppInfo list JSON                                      |                        |
      |                        |------------------------------------------------------->|                        |
      |                        |                                                        |                        |
      |                        | AppInfo List objects                                   |                        |
      |                        |<-------------------------------------------------------|                        |
      |                        |                                                                                 |
      | export_device_info()   |                                                                                 |
      |------------------------|                                                                                 |
      |                        |                                                                                 |
      | export_app_inventory() |                                                                                 |
      |------------------------|                                                                                 |
      |                        |                                                                                 |
      | update_job_status(COMPLETED)                                                                             |
      |--------------------------------------------------------------------------------------------------------->|
      v                        v                                                                                 v
```

---

## 2. Integration Tests Validation
To run the end-to-end integration pipeline tests simulating full device migrations:
```bash
python -m unittest shared.orchestrator.test_flow
```
This initializes an in-memory SQLite database, runs migrations, mocks the ADB server transport, executes the coordinator, and asserts database states and CSV data structures.

---

## 3. Sprint 1 Demo Acceptance Criteria

During the Sprint 1 demo, the following milestones must be achieved:

| Step | Operation | UI / CLI Indicator | Success Verification |
|:---|:---|:---|:---|
| **1** | Device Connection | UI status shifts to "Connected" | The `devices` table contains the connected serial, manufacturer, and model properties. |
| **2** | Transaction Startup | CLI logs show Job ID creation | A new job entry exists in the `backup_jobs` table marked as `STARTED`. |
| **3** | Scanning Execution | Progress bar moves dynamically | ADB logs show `pm list` and `pm dump` commands running successfully. |
| **4** | Reports Output | File Explorer opens export folder | Generated `device_summary_[serial].csv` and `apps_inventory_[serial].csv` reports are written atomically. |
| **5** | Neutralization Validation | View CSV report in editor | Applications containing formula control characters (`=`, `+`, `-`, `@`) are successfully prepended with `'`. |
| **6** | Transaction Closing | Status updates to "Completed" | The `backup_jobs` status is updated to `COMPLETED`, `readiness_score` is set to 100, and a finish time exists. |
