# Phoenix Backup Decision Suite: Risk Knowledge Base
## Role: Principal AI Architect
## Execution Context: 100% Offline (Local Client PC)
## Document Version: 1.0.0

This knowledge base details the recovery characteristics, data types, backup/restore constraints, and security risks associated with common Android applications. The Recovery Intelligence Engine audits these apps to evaluate user-readiness and compile explainable recovery guides.

---

## 1. Summary Matrix

| Application | Package Identifier | Risk Level | Primary Data Type | Backup Channel | Recovery Friction |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Google Authenticator** | `com.google.android.apps.authenticator2` | **CRITICAL** | TOTP Seed Keys | In-app QR Export (Manual) | **Extreme** (Requires manual scan or account recovery) |
| **Microsoft Authenticator**| `com.azure.authenticator` | **CRITICAL** | MFA & TOTP Seeds | Microsoft Cloud (In-App) | **High** (Requires Microsoft account credentials) |
| **Signal** | `org.thoughtcrime.securesms` | **CRITICAL** | Encrypted Chat DB | Local Encryption File | **High** (Requires 30-digit key and storage import) |
| **WhatsApp** | `com.whatsapp` | **CRITICAL** | Encrypted Databases & Media | Google Drive / Local Copy | **High** (SMS verification + Drive pull) |
| **Telegram** | `org.telegram.messenger` | **MEDIUM** | Cloud Chats & Local Secrets | Telegram Server (Cloud) | **Low** (Secret Chats are unrecoverable) |
| **Chase Mobile (Banking)** | `com.chase.sig.android` | **HIGH** | Session Keys & Device ID | None (Re-register only) | **High** (SMS verification + KYC questions) |
| **Bitwarden** | `co.bitwarden.app` | **HIGH** | Encrypted Vault Cache | Cloud Sync / Manual JSON | **Medium** (Master Password + 2FA) |
| **Google Photos (Gallery)** | `com.google.android.apps.photos` | **MEDIUM** | Media (DCIM/Pictures) | Cloud Sync / USB Copy | **Low** (Cloud re-sync or USB restore) |
| **Obsidian (Notes)** | `md.obsidian` | **HIGH** | Local Markdown Vaults | USB Folder Copy | **Medium** (Folder structural restore) |
| **Google Keep (Notes)** | `com.google.android.keep` | **LOW** | Cloud Notes | Google Account Sync | **None** (Auto sync on sign-in) |

---

## 2. Detailed Application Risk Profiles

### 2.1 Google Authenticator
*   **Package Identifier:** `com.google.android.apps.authenticator2`
*   **Risk Level:** **CRITICAL**
*   **Data Type:** TOTP (Time-based One-time Password) seed credentials.
*   **Backup Strategy:**
    *   Google Authenticator binds its secret keys to the Android Keystore system. ADB is unable to extract these credentials.
    *   *Strategy:* Trigger the manual account export option inside the app to consolidate all seeds into a single visual Transfer QR code.
*   **Recovery Requirements:** Scan the Transfer QR code using the camera on the newly initialized device.
*   **User Warning:**
    > [!CAUTION]
    > Wiping your device without exporting your Google Authenticator accounts will result in permanent lockout from all accounts protected by its 2FA codes.

---

### 2.2 Microsoft Authenticator
*   **Package Identifier:** `com.azure.authenticator`
*   **Risk Level:** **CRITICAL**
*   **Data Type:** Multi-Factor tokens, Azure AD corporate credentials, cloud-backed TOTP records.
*   **Backup Strategy:**
    *   *Strategy:* Enable "Cloud Backup" in the application settings menu. This saves encrypted credentials to the user's personal Microsoft account.
    *   *Note:* Backups created on Android cannot be restored on iOS due to cryptographic keychain differences.
*   **Recovery Requirements:** Log in to the identical Microsoft account on the target Android device to trigger database restoration.
*   **User Warning:**
    > [!WARNING]
    > Verify that 'Cloud Backup' is active and showing a green status indicator before wiping. Ensure you have access to your backup Microsoft Account from another active device.

---

### 2.3 Signal
*   **Package Identifier:** `org.thoughtcrime.securesms`
*   **Risk Level:** **CRITICAL**
*   **Data Type:** Local SQLCipher-encrypted database, cryptographic identities, and downloaded attachments.
*   **Backup Strategy:**
    *   Signal sets `allowBackup="false"`. No system tools can extract its sandbox.
    *   *Strategy:* Enable 'Chat Backups' in Signal Settings -> Chats. This generates a local encrypted `.backup` file on the storage partition.
*   **Recovery Requirements:**
    1.  Copy the 30-digit passphrase generated when turning on backups.
    2.  Transfer the backup file from `/sdcard/Signal/Backups/` to the host PC via USB/ADB.
    3.  Move this backup folder back onto the new device's storage before starting Signal for the first time.
*   **User Warning:**
    > [!IMPORTANT]
    > Signal stores zero chat data on its servers. Wiping the device without saving BOTH the backup file and the 30-digit passphrase will permanently delete your chats.

---

### 2.4 WhatsApp
*   **Package Identifier:** `com.whatsapp`
*   **Risk Level:** **CRITICAL**
*   **Data Type:** Encrypted chat databases, local media directories (documents, images, voice notes).
*   **Backup Strategy:**
    *   *Strategy:* Run an in-app backup to Google Drive (WhatsApp Settings -> Chats -> Chat backup).
    *   *Alternative (Local):* Copy the entire directory `/sdcard/Android/media/com.whatsapp/` to the host PC via ADB.
*   **Recovery Requirements:** Re-verify the telephone number on the target device via SMS OTP, then select 'Restore' from Google Drive or local storage media.
*   **User Warning:**
    > [!WARNING]
    > Local database files require the original decryption key stored inside WhatsApp's private sandbox. If you do not have Google Drive sync enabled, you must copy the media folders and register with the same phone number to decrypt files.

---

### 2.5 Telegram
*   **Package Identifier:** `org.telegram.messenger`
*   **Risk Level:** **MEDIUM**
*   **Data Type:** Server-synced chat history, cached media, local-only Secret Chats.
*   **Backup Strategy:**
    *   *Strategy:* Cloud chats are stored on Telegram servers and do not need local backup.
    *   *Secret Chats:* Are device-specific and bound to keys in the local sandbox. They cannot be backed up.
*   **Recovery Requirements:** Sign in on the new device, complete SMS OTP verification, and enter the password (if 2-Step Verification is active).
*   **User Warning:**
    > [!NOTE]
    > All active 'Secret Chats' will be destroyed when the old device is reset. Normal chats, groups, and channels will sync automatically upon logging in.

---

### 2.6 Chase Mobile (Representative Banking App)
*   **Package Identifier:** `com.chase.sig.android`
*   **Risk Level:** **HIGH**
*   **Data Type:** Session tokens, cached statements, biometric configuration parameters.
*   **Backup Strategy:**
    *   No backup is possible. Financial institutions strictly disable backup agents and tie sessions to unique hardware identifiers.
*   **Recovery Requirements:**
    1.  Re-download the application on the target device.
    2.  Log in using credentials (username and password).
    3.  Complete identity verification (SMS/Email OTP or call-in verification).
*   **User Warning:**
    > [!IMPORTANT]
    > Wiping your device will revoke its authorization as a trusted login device. Ensure you know your online banking username, password, and security answers beforehand.

---

### 2.7 Bitwarden (Representative Password Manager)
*   **Package Identifier:** `co.bitwarden.app`
*   **Risk Level:** **HIGH**
*   **Data Type:** Offline encrypted credential database, secure notes, Master Password configurations.
*   **Backup Strategy:**
    *   *Strategy:* Synchronize the local vault with the Bitwarden cloud server before wiping.
    *   *Alternative:* Export a password-protected JSON vault backup file from the Bitwarden desktop or web interface.
*   **Recovery Requirements:** Install the app, log in using the Master Password, and verify authorization via your designated 2FA channel.
*   **User Warning:**
    > [!CAUTION]
    > Make sure you know your Bitwarden Master Password. If your vault is locked and you forget the Master Password, there is no recovery option.

---

### 2.8 Google Photos (Representative Gallery App)
*   **Package Identifier:** `com.google.android.apps.photos`
*   **Risk Level:** **MEDIUM**
*   **Data Type:** User photos, video recordings, metadata.
*   **Backup Strategy:**
    *   *Strategy 1 (Cloud):* Verify that "Backup & Sync" status is shown as "Backup complete" inside the application profile menu.
    *   *Strategy 2 (Local):* Copy `/sdcard/DCIM/` and `/sdcard/Pictures/` to the host PC via ADB.
*   **Recovery Requirements:** Sign into the identical Google account on the target device to sync files, or copy the media directory back via USB.
*   **User Warning:**
    > [!NOTE]
    > Photos that are not fully synced to the cloud or copied to a PC will be permanently deleted during a factory reset.

---

### 2.9 Obsidian
*   **Package Identifier:** `md.obsidian`
*   **Risk Level:** **HIGH**
*   **Data Type:** Markdown files, plugin configurations, local workspace setups.
*   **Backup Strategy:**
    *   Obsidian stores its vault contents entirely locally on storage unless the user pays for Obsidian Sync.
    *   *Strategy:* Copy your vault directories (typically located in `/sdcard/Documents/` or `/sdcard/Obsidian/`) to the PC.
*   **Recovery Requirements:** Install Obsidian on the new device, create a vault directory, and copy your backup files into it.
*   **User Warning:**
    > [!WARNING]
    > Obsidian does not sync notes to a free cloud service. Notes must be manually backed up over USB to prevent loss.

---

### 2.10 Google Keep
*   **Package Identifier:** `com.google.android.keep`
*   **Risk Level:** **LOW**
*   **Data Type:** Notes, checklists, drawings, voice recordings.
*   **Backup Strategy:**
    *   Automatically synchronized in real-time to the user's Google account cloud backend.
*   **Recovery Requirements:** Log in to the Google account on the target device.
*   **User Warning:**
    > [!NOTE]
    > Ensure that sync for 'Google Keep' is active under Settings -> Accounts -> Google Account Sync.
