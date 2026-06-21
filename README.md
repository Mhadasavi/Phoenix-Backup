# Phoenix Backup: AI-Powered Android Backup & Recovery Assistant

Phoenix Backup is a secure, cross-platform Android backup and recovery auditer. It features a React-based Electron desktop control panel, a headless Android companion app, and a Python-based analysis and data extraction backend.

---

## 1. Monorepo Workspace Structure

*   **`desktop/`**: Electron application (TypeScript) with a React (TSX) dashboard. Coordinates device scanning, logs real-time status, and manages local SQLite storage.
*   **`android/`**: Native Java companion app. Runs a secure, loopback-only (`127.0.0.1`) TCP server, using HMAC-SHA256 authenticated handshakes to prevent unauthorized data extraction.
*   **`shared/`**: Unified Python backend modules:
    *   `shared/adb/`: Secure ADB wrapper for device discovery and package auditing.
    *   `shared/db/`: Database connection manager and SQLite transactional import service (`import_service.py`).
    *   `shared/network/`: Secure socket transport client with HMAC authentication framing (`client.py`).
    *   `shared/intelligence/`: Risk auditor, vulnerability scoring model, and recommendations findings engine.
    *   `shared/export/`: Dynamic HTML and PDF readiness report generation engines.
    *   `shared/orchestrator/`: E2E data extraction backup runner (`backup_runner.py`).

---

## 2. Sprint 3 Data Extraction Architecture

Sprint 3 implements secure, high-performance data extraction slices:
1.  **Secure Handshake**: The desktop client establishes an ADB port forward tunnel and authenticates using an HMAC-SHA256 token exchange.
2.  **Contacts Slice**: Queries name, phone numbers, and emails using optimized bulk queries.
3.  **SMS Slice**: Extracts text messages paginated via modern `Bundle` parameters.
4.  **Call History Slice**: Retrieves call logs with support for private/withheld caller IDs (empty strings).
5.  **Persistence**: Automatically writes extracted records into the host-side SQLite database.

---

## 3. Quick Start Guide

For full details, see [BUILD_AND_RUN.md](file:///j:/Repo/Resources/Android/phoenix-backup/BUILD_AND_RUN.md) and [BUILD_ANDROID.md](file:///j:/Repo/Resources/Android/phoenix-backup/android/BUILD_ANDROID.md).

### Prerequisites
*   **Java 17 (JDK)** (for compiling the Android app)
*   **Android SDK Platform Tools (ADB)** (configured in system PATH)
*   **Node.js v20+** & **NPM v10+**
*   **Python v3.10+**

### Dev Setup & Bootstrapping
```powershell
# 1. Bootstrap monorepo workspaces and download Electron binary assets
npm run bootstrap
node node_modules/electron/install.js

# 2. Compile and install the Android Companion APK
cd android
.\gradlew.bat assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk

# 3. Grant companion permissions via ADB
adb shell pm grant com.phoenix.companion android.permission.READ_SMS
adb shell pm grant com.phoenix.companion android.permission.READ_CONTACTS
adb shell pm grant com.phoenix.companion android.permission.READ_CALL_LOG

# 4. Start the companion app foreground service
adb shell am start-foreground-service -n com.phoenix.companion/.service.BackupService --es token sprint2_integrated_salt

# 5. Launch the Desktop Dashboard Control Panel
cd ..
npm run dev:desktop
```

---

## 4. Running the Test Suite

We maintain a high-coverage test suite across all modules:

*   **Android Companion JVM Tests**:
    ```powershell
    cd android
    .\gradlew.bat test
    ```
*   **Python Shared Module Tests**:
    ```powershell
    python -m unittest discover -s shared -p "test_*.py"
    ```
*   **System End-to-End Integration Tests**:
    ```powershell
    python -m unittest discover -s tests -p "test_*.py"
    ```
