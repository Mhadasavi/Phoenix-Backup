# Building and Running the Phoenix Companion App on Windows 11

This guide provides instructions on how to set up your Windows 11 environment, compile the companion Android application, and deploy it to a physical device or emulator.

---

## 1. Prerequisites & Environment Setup

### Java Development Kit (JDK)
- **Required Version:** **JDK 17**
- Download and install JDK 17 (e.g., Eclipse Temurin or Oracle OpenJDK).
- Ensure your `JAVA_HOME` environment variable points to the JDK 17 installation directory.
- Verify in PowerShell:
  ```powershell
  java -version
  ```

### Android Studio Setup
1. Download and install [Android Studio (Hedgehog 2023.1.1 or newer)](https://developer.android.com/studio).
2. During setup, choose standard options to install the Android SDK.
3. Open Android Studio, navigate to **Tools > SDK Manager**:
   - Under **SDK Platforms**, check **Android 14.0 ("UpsideDownCake")** (API Level 34).
   - Under **SDK Tools**, check **Android SDK Build-Tools 34** and **Android SDK Platform-Tools** (which installs `adb`).
4. Find your SDK path (typically `C:\Users\<Username>\AppData\Local\Android\Sdk`).

### Project SDK Mapping
Ensure `android/local.properties` contains the path to your Android SDK. If it does not exist, create it:
```properties
sdk.dir=C\:/Users/<Your-Username>/AppData/Local/Android/Sdk
```
*(Note: Use forward slashes `/` and escape the colon `:` with a backslash).*

---

## 2. Project Specifications

- **Language:** Java 17
- **Minimum SDK:** API Level 30 (Android 11)
- **Target SDK:** API Level 34 (Android 14)
- **Gradle Wrapper Version:** 8.4
- **Android Gradle Plugin (AGP):** 8.2.0

---

## 3. Build Commands

Run all commands from the `android` subdirectory of the repository using PowerShell.

### Clean Project
Before building, clean any cached files:
```powershell
./gradlew clean
```

### Run Unit Tests
To execute all local JVM unit tests and generate HTML reports:
```powershell
./gradlew test
```
*Report location:* `android/app/build/reports/tests/testDebugUnitTest/index.html`

### Generate Debug APK
Compiles the application with debugging enabled (unsigned/debug-signed):
```powershell
./gradlew assembleDebug
```
*Output Path:* `android/app/build/outputs/apk/debug/app-debug.apk`

### Generate Release APK
Compiles the application in release mode:
```powershell
./gradlew assembleRelease
```
*Output Path:* `android/app/build/outputs/apk/release/app-release-unsigned.apk`
*(Note: To install a release build on a physical device, it must be signed using `apksigner` and a local keystore).*

---

## 4. ADB Installation and Execution

Ensure your Android device has **Developer Options** and **USB Debugging** enabled. Connect the device via USB.

### Verify Device Connection
```powershell
adb devices
```
*(Ensure your device is listed and shows `device` status).*

### Install the Debug APK
```powershell
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### Grant Extraction Permissions
Since the companion app is a zero-UI headless service, permissions must be granted manually via ADB (unless a launcher Activity is added to request them):
```powershell
adb shell pm grant com.phoenix.companion android.permission.READ_SMS
adb shell pm grant com.phoenix.companion android.permission.READ_CONTACTS
adb shell pm grant com.phoenix.companion android.permission.READ_CALL_LOG
```

### Start the Sync Service
Start the companion service in the foreground, passing the authentication handshake token:
```powershell
adb shell am start-foreground-service -n com.phoenix.companion/.service.BackupService --es "token" "sprint2_integrated_salt"
```

### Stop the Sync Service
To manually shut down the companion:
```powershell
adb shell am stopservice -n com.phoenix.companion/.service.BackupService
```

### Establish Port Forwarding
Set up the ADB tunnel to map the local desktop backup client port to the companion service port:
```powershell
adb forward tcp:50051 tcp:50051
```
The desktop script can now connect securely to `127.0.0.1:50051`.

---

## 5. Troubleshooting Guide

### Issue: `SDK location not found`
- **Error:** Gradle fails complaining that the SDK location is not defined.
- **Solution:** Verify `local.properties` exists in the `android/` directory and contains:
  ```properties
  sdk.dir=C\:/Users/<Your-Username>/AppData/Local/Android/Sdk
  ```
  Double-check that the username matches your Windows account name and the folder exists.

### Issue: `Duplicate class found in modules`
- **Error:** Build fails with `CheckDuplicatesRunnable` pointing to duplicate Kotlin stdlib classes (e.g. `kotlin-stdlib-jdk8`).
- **Solution:** The project configuration includes a `configurations.all` block in `app/build.gradle` that forces all Kotlin stdlib components to `1.8.22` to resolve transitive dependency conflicts. Run `./gradlew clean` and rebuild.

### Issue: `ForegroundServiceStartNotAllowedException` on Android 12+
- **Error:** Service fails to start when launched in the background.
- **Solution:** Android 12+ restricts starting foreground services from the background. Launching the service via `adb shell am start-foreground-service` is an allowed exception and will work during development. For production use, starting the service must be initiated from a user-visible UI Activity.

### Issue: `adb: command not found`
- **Error:** PowerShell does not recognize `adb`.
- **Solution:** Add the Android Platform Tools directory to your Windows user Environment PATH:
  `C:\Users\<Your-Username>\AppData\Local\Android\Sdk\platform-tools`
  Alternatively, reference it directly:
  `& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" devices`
