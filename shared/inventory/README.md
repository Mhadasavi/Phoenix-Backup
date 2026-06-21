# App Inventory Module - Phoenix Backup

This module is responsible for querying installed package profiles, extracting app details (apk path, package identifier, version name/code), and checking system partition levels.

## Features:
1.  **Lightweight Crawling:** Executes the whitelisted `pm list packages -f` shell commands to gather installed apps and their file system paths.
2.  **Version Extraction:** Queries version details using the whitelisted `pm dump <package>` command, running regular expression matchers for `versionName` and `versionCode` metrics.
3.  **Partition Categorization:** Automatically flags apps residing in system mounts (`/system`, `/vendor`, `/apex`, `/product`) as `is_system` apps.
4.  **Tokenized Display Name Fallback:** Derives user-facing app names from package path structures (e.g. `com.whatsapp` -> "Whatsapp") when companion services are offline.

## Usage:
```python
from shared.adb.wrapper import AdbWrapper
from shared.inventory.manager import AppInventoryManager

# Initialize adb client
adb = AdbWrapper()

# Initialize inventory crawler
inv_manager = AppInventoryManager(adb)

# Query user apps (third-party only)
apps = inv_manager.get_installed_apps(serial="emulator-5554", include_system=False)
for app in apps:
    print(f"App: {app.app_name} | Package: {app.package_name} (v{app.version_name})")
    print(f"  Path: {app.apk_path}")
```

## Running Unit Tests:
```bash
python -m unittest shared.inventory.test_manager
```
