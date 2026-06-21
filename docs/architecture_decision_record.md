# Phoenix Backup: Architecture Decision Records (ADR)
## Role: Principal Android Architect & Security Architect
## Execution Context: 100% Offline (Local Client PC)
## Document Version: 1.0.0

---

## ADR 001: Dynamic Manifest and Heuristic Backup Flag Analysis

### Context
To calculate the Recovery Readiness Score and flag app data loss hazards, Phoenix Backup must determine the `allowBackup` flag status for all installed Android packages. The original proposal was to assume a default of `allowBackup=true` and override to `false` using package patterns in `app_rules.json`.

### Evaluation

#### Technical Correctness
*   **Android Default behavior:** In Android, the default value of `allowBackup` is `true` if not declared in the manifest (pre-Android 12/API 31). Starting with Android 12, Google modified this behavior so that while system backups are still allowed, third-party ADB backups are blocked by default for user-installed applications.
*   **Verdict:** Assuming `allowBackup=true` as a universal default is technically incorrect for Android 12+ (API 31+) devices regarding ADB extraction.

#### Android Platform Limitations
*   Reading the `AndroidManifest.xml` directly requires pulling the APK file to the host PC and parsing it using tools like `AxmlParser` or `apktool`, or executing `dumpsys package <package_name>` and parsing the output flags.
*   `dumpsys package` requires querying each package individually, introducing latency when processing large inventories ($500+$ apps).

#### False Positive Risks (Flagging an app as secure when it is actually blocked)
*   **High Risk:** If the system assumes `allowBackup=true`, but the app declares `allowBackup="false"` or is running on Android 12+ where ADB backup is ignored, Phoenix will give a false sense of security, leading to permanent user data loss.

#### False Negative Risks (Flagging an app as blocked when it is actually secure)
*   **Low Risk:** Flagging an app as blocked simply prompts the user to perform a manual verification checklist. While annoying, it guarantees data safety.

#### Long-Term Maintainability
*   Relying solely on a static dictionary like `app_rules.json` creates a maintenance bottleneck, requiring updates whenever new apps are released.

---

### Decision Classification
*   **Decision:** **MODIFY**

### Recommended v1 Decision
For Phoenix Backup v1, we will implement a **Layered Resolution Strategy**:
1.  **Rule Match Check:** Consult `app_rules.json` first. If a package is matched, use the explicit severity and backup configuration.
2.  **API Level Heuristic:** If the package is unknown and target device `api_level >= 31` (Android 12+), assume `allowBackup=false` for all non-system user applications. If `api_level < 31`, assume `allowBackup=true`.
3.  **Local Manifest Extraction Fallback:** For any app classified as high-risk, execute a targeted `dumpsys package <package_name>` command over ADB. The parser will search the output for backup flags (e.g. `backupAgent`, `allowBackup=false`) to determine status dynamically without pulling the raw APK.

### Future Roadmap Decision
Implement an on-device manifest indexer inside the **Android Companion App** (Sprint 2). The companion app will read package manifest attributes locally using `PackageManager.getPackageInfo(flags)`, serialize them, and transfer the index database in a single TCP socket stream to the host PC, eliminating ADB CLI parsing bottlenecks.

### Risk Assessment
*   *Performance Cost:* Executing `dumpsys package` takes roughly $50\text{ms}$ per query. Limiting queries to unknown packages flagged as high-risk keeps execution time low.
*   *Security Isolation:* No files are transferred to the host PC during metadata inspection, maintaining privacy.

### Required Schema Changes
Extend the `device_app_inventory` SQLite table to track the `backup_source` flag (e.g., `RULE_MATCH`, `HEURISTIC_API`, `DUMPSYS_RESOLVED`).

---
---

## ADR 002: Storage Sync Verification Metrics

### Context
To calculate the media/storage backup progress metric $S_{\text{storage}}$, the engine must audit target directory sizes on the Android filesystem and verify that the corresponding files exist on the host PC's backup destination. The original proposal was to use mock folders in tests and calculate sizes based on standard file stats.

### Evaluation

#### Accuracy
*   File statistics retrieved over ADB using standard shell calls (like `ls` or `find`) must account for file system differences (FAT32/ext4/sdcardfs) and hidden files.
*   Using simple mock folders in test cases does not catch file system permission blocks.

#### Performance
*   Running individual ADB commands to query thousands of photos inside `/sdcard/DCIM/` is slow.
*   Executing a single recursive search, e.g. `find /sdcard/DCIM/ -type f -exec stat ...` is more efficient but prone to shell buffer overflows.

#### Scalability & Multi-Device Support
*   Storage mounts vary by OEM (Samsung uses different folder layouts than Google Pixel or Xiaomi).
*   System filesystems block access to `/sdcard/Android/data/` on Android 11+ due to Scoped Storage security limits.

#### Android Storage Access Limitations
*   Beginning with Android 11 (API 30), standard applications cannot access files outside their own directories. However, commands run via ADB shell (which execute under the shell UID `2000`) bypass these constraints and can read general `/sdcard/` files.

---

### Decision Classification
*   **Decision:** **MODIFY**

### Recommended v1 Decision
For Phoenix Backup v1, we will implement a **Two-Pass Storage Auditor**:
1.  **Device-Side Directory Inventory (Pass 1):** The desktop app executes a single, optimized ADB shell query to retrieve directory totals:
    ```bash
    adb shell du -a -k /sdcard/DCIM /sdcard/Pictures /sdcard/Documents /sdcard/Download
    ```
    This returns a flat file listing relative paths, sizes in kilobytes, and modification dates.
2.  **Host-Side Sync Verification (Pass 2):** The desktop app scans the local backup target directory on the PC, compares it against the device manifest, and verifies the sizes match.
3.  **Readiness Score Impact:**
    $$S_{\text{storage}} = 55 \times \frac{\sum \text{BytesSynced}(d)}{\sum \text{TotalBytes}(d)}$$

### Future Roadmap Decision
Integrate a Media Database parser into the **Android Companion App**. The companion app will query the Android `MediaStore` ContentProvider directly. This returns a database of media files with size and hashing info in under $500\text{ms}$, bypassing the file system traversal latency of shell utilities.

### Risk Assessment
*   *Access Blocks:* Some OEMs protect user directories. If `du` fails due to permission blocks, the engine falls back to standard `ls -l` commands.
*   *Checksum Collisions:* In v1, size-matching is used instead of hashing to keep latency low. Hashing is deferred to the future roadmap.

### Required Schema Changes
Add a table to track file sync metadata:
```sql
CREATE TABLE IF NOT EXISTS device_storage_manifest (
    device_id TEXT NOT NULL,
    directory_path TEXT NOT NULL,
    total_bytes INTEGER NOT NULL,
    synced_bytes INTEGER NOT NULL DEFAULT 0,
    last_verified DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(device_id, directory_path),
    FOREIGN KEY(device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);
```
