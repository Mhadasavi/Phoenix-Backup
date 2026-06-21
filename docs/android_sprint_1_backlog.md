# Android Companion App Implementation Backlog
## Project: Phoenix Backup Mobile Agent (Sprint 1)
### Target Focus: Core Infrastructure, Sockets, and Data Extractors

This backlog outlines the technical task breakdowns for implementing the Java-based Android companion application.

---

## 1.1 Dependency Ordering & Task Tree

```
  TASK-ANDR-001: Java Gradle Project Init
        ├── TASK-ANDR-002: Android Manifest & Permission Setup
        │        ├── TASK-ANDR-003: Foreground Service & WakeLocks
        │        │        └── TASK-ANDR-004: Local Socket Server Binding
        │        │                 └── TASK-ANDR-005: Handshake Token Authenticator
        │        │                          └── TASK-ANDR-009: Command Dispatcher
        │        ├── TASK-ANDR-007: Contacts Extractor ─────────────┤
        │        └── TASK-ANDR-008: SMS & Call Logs Extractors ─────┤
        └── TASK-ANDR-006: Device Metadata Extractor ──────────────┘
```

---

## 1.2 Backlog Task Specifications

### TASK-ANDR-001: Java Android Project Initialization
* **Priority:** Blocker (Must Have)
* **Dependencies:** None.
* **Technical Description:** Setup the Android Gradle project under the `/android` directory, configuring compiler options for Java 17 and SDK targets 30 to 34+.
* **Acceptance Criteria:**
  - The project compiles successfully via Gradle wrapper `./gradlew assembleDebug` yielding a valid base APK.
* **Testing Requirements:** Run compile verification on the CLI. Assert that the generated package builds with zero compiler warnings.

### TASK-ANDR-002: Android Manifest & Permissions Declarations
* **Priority:** Blocker (Must Have)
* **Dependencies:** TASK-ANDR-001
* **Technical Description:** Write the `AndroidManifest.xml` registering system queries, service declarations with foreground sync types, and required runtime/system permissions.
* **Acceptance Criteria:**
  - Manifest includes all permissions: `READ_SMS`, `READ_CONTACTS`, `READ_CALL_LOG`, `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_DATA_SYNC`, `WAKE_LOCK`, and `QUERY_ALL_PACKAGES`.
  - App queries block includes `<queries>` to support package inventory visibility.
* **Testing Requirements:** Inspect the compiled APK manifest using `aapt2 dump badging` to confirm all permissions and service declarations are embedded.

### TASK-ANDR-003: Foreground Service & CPU WakeLocks
* **Priority:** Critical (Must Have)
* **Dependencies:** TASK-ANDR-002
* **Technical Description:** Implement `BackupService.java` extending `android.app.Service`. Configure notification channels, call `startForeground()`, and handle partial `WakeLock` hooks.
* **Acceptance Criteria:**
  - Launching the service via shell command triggers a sticky system notification:
    `adb shell am start-foreground-service com.phoenix.companion/.BackupService`
  - The CPU remains awake (verifiable via system power logs) while the service runs.
* **Testing Requirements:** Write a JUnit integration test verifying that starting the service configures a valid notification channel and active WakeLock flags.

### TASK-ANDR-004: Local Loopback Server Socket Binding
* **Priority:** Critical (Must Have)
* **Dependencies:** TASK-ANDR-003
* **Technical Description:** Implement `SocketServer.java` listening strictly on loopback interface `127.0.0.1:50051`.
* **Acceptance Criteria:**
  - The server binds successfully on port `50051`.
  - Port scans from external interfaces (Wi-Fi) show port `50051` is closed, confirming loopback-only isolation.
* **Testing Requirements:** Start the server on a test emulator. Attempt to connect to `50051` from the host PC using loopback (successful) and from a secondary network device (rejected).

### TASK-ANDR-005: Handshake Token Authenticator
* **Priority:** Critical (Must Have)
* **Dependencies:** TASK-ANDR-004
* **Technical Description:** Implement `SessionAuthenticator.java` to read and match the handshake token passed in the launch intent.
* **Acceptance Criteria:**
  - Sockets sending a matching token remain open.
  - Sockets sending mismatching tokens are immediately closed.
* **Testing Requirements:** Write unit tests using mock sockets, asserting that sending correct keys returns a success state, and invalid keys throw unauthorized closures.

### TASK-ANDR-006: Device Metadata Extractor
* **Priority:** High (Must Have)
* **Dependencies:** TASK-ANDR-001
* **Technical Description:** Implement `SystemMetadataHelper.java` extracting `Build.MANUFACTURER`, `Build.MODEL`, and filesystem block sizes.
* **Acceptance Criteria:**
  - The helper successfully compiles details into JSON matching the api contract.
* **Testing Requirements:** Run unit tests asserting that output strings contain valid manufacturer and API integers.

### TASK-ANDR-007: Contacts Content Provider Extractor
* **Priority:** High (Must Have)
* **Dependencies:** TASK-ANDR-002
* **Technical Description:** Implement `ContactsProviderHelper.java` reading from `ContactsContract` using query cursors with limit/offset pagination.
* **Acceptance Criteria:**
  - Queries return compiled JSON arrays of contact names, phone numbers, and emails.
  - Revoking permissions returns a clean error status rather than causing app crashes.
* **Testing Requirements:** Write instrumented database tests injecting mock contacts and validating JSON mapping outputs.

### TASK-ANDR-008: SMS & Call Logs Content Provider Extractors
* **Priority:** High (Must Have)
* **Dependencies:** TASK-ANDR-002
* **Technical Description:** Implement `SmsProviderHelper.java` and `CallLogProviderHelper.java` reading from `content://sms` and `CallLog` databases.
* **Acceptance Criteria:**
  - Queries return JSON records for message threads and call history records.
* **Testing Requirements:** Write instrumented tests using mock cursors verifying timestamp conversions to UTC milliseconds.

### TASK-ANDR-009: Command Dispatcher Interface Integration
* **Priority:** High (Must Have)
* **Dependencies:** TASK-ANDR-005, TASK-ANDR-006, TASK-ANDR-007, TASK-ANDR-008
* **Technical Description:** Implement `CommandDispatcher.java` to parse JSON commands from the socket stream and route them to the appropriate extractor helper classes.
* **Acceptance Criteria:**
  - Sending `GET_SYSTEM_INFO` over the socket returns device metadata.
  - Sending `GET_SMS` streams message records.
* **Testing Requirements:** Run socket-level E2E integration tests sending JSON requests and asserting the parsed outputs match.
