# Android Companion App Architectural Design Document
## Project: Phoenix Backup Mobile Agent
### Version: 1.0.0
### Platform Target: Android 11+ (API 30+)
### Language: Java 17

This document defines the system architecture, module structures, security controls, and permission frameworks for the Java-based Android companion application.

---

## 1. Architectural Overview

The companion app acts as a zero-UI system agent on the Android target. It operates as a local loopback server, exposing read-only data queries to the host desktop client via ADB port forwarding.

```
+-----------------------------------------------------------------------------------+
|                            ANDROID COMPANION ARCHITECTURE                         |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  | NETWORK LAYER (com.phoenix.companion.network)                               |  |
|  | - ServerSocket (Binds strictly to 127.0.0.1:50051)                           |  |
|  | - SessionHandshakeHandler (Token verification)                              |  |
|  | - StreamChunker (Length-prefixed JSON writer)                               |  |
|  +-------------------------------------+---------------------------------------+  |
|                                        |                                          |
|                                        v Data Requests                            |
|  +-------------------------------------+---------------------------------------+  |
|  | DOMAIN / CORE LAYER (com.phoenix.companion.core)                            |  |
|  | - ForegroundService (Lifecycle manager, WakeLocks)                          |  |
|  | - CommandDispatcher (Routes actions to extractors)                          |  |
|  +-------------------------------------+---------------------------------------+  |
|                                        |                                          |
|                                        v Extractor Commands                       |
|  +-------------------------------------+---------------------------------------+  |
|  | DATA / EXTRACTOR LAYER (com.phoenix.companion.data)                         |  |
|  | - SmsExtractor (content://sms/)                                             |  |
|  | - CallLogExtractor (content://call_log/calls)                               |  |
|  | - ContactsExtractor (ContactsContract)                                      |  |
|  | - SystemInfoExtractor (Build parameters, space stats)                       |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

### Key Structural Patterns:
* **Foreground Service Lifecycle:** Runs within an Android `Service` context, registering a `dataSync` foreground type to prevent OS sleep termination during network transfers.
* **Producer-Consumer Streaming:** Content Provider query results are read, serialized to JSON, and piped directly to the network socket in buffered pages (rather than loading the entire database into memory).
* **Dependency Injection (Manual):** To keep the binary size minimal, the application uses simple manual constructor injection instead of frameworks like Dagger or Hilt.

---

## 2. Module Breakdown

The companion app is organized into a modular Java package layout under the root namespace `com.phoenix.companion`:

1. **`com.phoenix.companion.service` (Lifecycle Orchestration):**
   * *`BackupService.java`*: Spawns the foreground notification, requests partial CPU `WakeLock` hooks, and launches the TCP network listener thread.
2. **`com.phoenix.companion.network` (Loopback Communication):**
   * *`SocketServer.java`*: Manages socket bindings and parses length-prefixed protocol frames.
   * *`SessionAuthenticator.java`*: Handles cryptographic token comparison during the connection handshake.
3. **`com.phoenix.companion.data` (Content Provider Extractors):**
   * *`SmsProviderHelper.java`*: Queries message databases.
   * *`CallLogProviderHelper.java`*: Queries call logs.
   * *`ContactsProviderHelper.java`*: Reads ContactsContract profiles.
   * *`SystemMetadataHelper.java`*: Reads system properties (`android.os.Build`) and filesystem blocks.
4. **`com.phoenix.companion.security` (Access Controls):**
   * *`PermissionChecker.java`*: Validates runtime permissions dynamically before querying providers.

---

## 3. Permission Matrix

Modern Android (API 30+) requires explicit manifest declarations and runtime approvals. The companion app bypasses UI prompts by utilizing automated ADB permission grants during onboarding.

| Permission Identifier | Scope Type | Target API | Architectural Rationale | ADB Grant Bypass Command |
|:---|:---|:---|:---|:---|
| `android.permission.READ_SMS` | Runtime | 26+ | Required to query message histories via `content://sms/` content resolvers. | `adb shell pm grant com.phoenix.companion android.permission.READ_SMS` |
| `android.permission.READ_CONTACTS` | Runtime | 26+ | Required to crawl contact vCard profiles via `ContactsContract`. | `adb shell pm grant com.phoenix.companion android.permission.READ_CONTACTS` |
| `android.permission.READ_CALL_LOG` | Runtime | 26+ | Required to fetch call history parameters via call resolvers. | `adb shell pm grant com.phoenix.companion android.permission.READ_CALL_LOG` |
| `android.permission.FOREGROUND_SERVICE` | Normal | 28+ | Required to run background data crawlers without OS sleep interruptions. | *Auto-granted at install.* |
| `android.permission.FOREGROUND_SERVICE_DATA_SYNC` | Normal | 34+ | Required on Android 14+ to declare dataSync service types. | *Auto-granted at install.* |
| `android.permission.WAKE_LOCK` | Normal | 26+ | Allows acquiring partial CPU WakeLocks during network operations. | *Auto-granted at install.* |
| `android.permission.QUERY_ALL_PACKAGES` | Signature / Sideload | 30+ | Required on Android 11+ to read the complete list of installed packages. | *Auto-granted for sideloaded ADB installations.* |

---

## 4. Data Flow Diagrams

### 4.1 Connection & Handshake Execution
```
  [Host PC Electron App]                  [ADB Port Forward]               [Companion SocketServer]
           |                                       |                                    |
           | 1. adb shell am start-service ...     |                                    |
           |---------------------------------------+----------------------------------->|
           |                                       |                                    | [BackupService]
           |                                       |                                    | - Starts Foreground notification
           |                                       |                                    | - Receives auth_token
           |                                       |                                    | - Binds ServerSocket (127.0.0.1)
           |                                       |                                    |
           | 2. adb forward tcp:50051 tcp:50051    |                                    |
           |-------------------------------------->|                                    |
           |                                       |                                    |
           | 3. Connect to 127.0.0.1:50051         |                                    |
           |---------------------------------------+----------------------------------->|
           |                                       |                                    |
           | 4. Send "AUTHENTICATE" JSON           |                                    |
           |    (with auth_token)                  |                                    |
           |---------------------------------------+----------------------------------->|
           |                                       |                                    | [SessionAuthenticator]
           |                                       |                                    | - Matches token
           |                                       |                                    | - If valid, returns SUCCESS
           |                                       |                                    | - If invalid, terminates socket
           |<--------------------------------------+------------------------------------|
```

### 4.2 Stream-Based Data Extraction Flow (Contacts example)
```
  [SocketServer]                   [CommandDispatcher]               [ContactsExtractor]
        |                                   |                                 |
        | 1. GET_CONTACTS (limit, offset)   |                                 |
        |---------------------------------->|                                 |
        |                                   | 2. fetchContacts()              |
        |                                   |-------------------------------->|
        |                                   |                                 | [ContactsProviderHelper]
        |                                   |                                 | - Checks runtime permissions
        |                                   |                                 | - Runs cursor queries
        |                                   |                                 | - Serializes records to JSON
        |                                   | 3. Return serialized data       |
        |                                   |<--------------------------------|
        | 4. Write length-prefixed packet   |                                 |
        |    to Socket stream               |                                 |
        v                                   v                                 v
```

---

## 5. Security Model

* **Interface Isolation (Localhost-Only):** The `ServerSocket` binds strictly to the loopback interface (`127.0.0.1`). This prevents remote devices on the same local network (Wi-Fi) from scanning or querying the TCP port.
* **Shared-Token Authentication:** Upon launching the service via ADB, the host PC passes a cryptographically secure, random token (e.g. 32-character hex) as a service extra parameter:
  `am start-foreground-service -n com.phoenix.companion/.BackupService --es token <random_hex>`
  Any client connecting to the TCP socket must send this token in the handshake frame. The server immediately closes connections with invalid tokens.
* **Least Privilege Enforcement (No Root):** The app runs entirely in standard Android user context. It does not execute shell elevation commands or require superuser permissions.
* **PII Protection:** The application does not store, cache, or write contacts, SMS, or call log data to the device filesystem. Data read from system database cursors is serialized directly to the socket stream in memory.

---

## 6. Testing Strategy

### 6.1 Local Java Unit Tests (Runner: JUnit 4)
* **Target:** Core parser and serialization logic.
* **Test Case Scenarios:**
  * Validate JSON generation parameters for various Android properties.
  * Verify `SessionAuthenticator` rejects mismatching tokens.
  * Verify command parser routes unknown actions to structured error responses.

### 6.2 Android Instrumented Tests (Runner: AndroidJUnitRunner)
* **Target:** Content Provider cursor execution.
* **Mock Context:** Use `ProviderTestCase2` or mock cursor builders to mock Contacts/SMS table states.
* **Test Case Scenarios:**
  * Verify `SmsProviderHelper` queries read-only content providers and handles empty rows correctly.
  * Verify `PermissionChecker` returns `PERMISSION_DENIED` errors if runtime permissions are revoked, and does not cause app crashes.
