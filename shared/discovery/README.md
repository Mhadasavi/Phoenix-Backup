# Device Discovery Module - Phoenix Backup

This module is responsible for discovering USB-connected Android devices, parsing system metadata properties, and evaluating partition storage capacities.

## Features:
1.  **Lightweight Discovery Scans:** Device status is scanned without querying device properties.
2.  **Lazy Property Extraction:** Detailed property parameters (Manufacturer, model, OS release, API Level) are fetched only when the device status maps to `device`.
3.  **Scoped-Storage Bypassing Capacity Check:** Uses Android's whitelisted `stat` utility to query block size stats from the `/data` mount, avoiding wide Android storage app permissions.
    *   *Command Executed:* `stat -f -c "%b|%f|%S" /data`
    *   *Calculation:* `bytes = blocks * block_size`

## Usage:
```python
from shared.adb.wrapper import AdbWrapper
from shared.discovery.detector import DeviceDetector

# Initialize the adb wrapper
adb_client = AdbWrapper()

# Initialize the discovery scanner
detector = DeviceDetector(adb_client)

# Run device scanner
devices = detector.detect_devices()
for dev in devices:
    print(f"Device: {dev.manufacturer} {dev.model} (OS: {dev.android_version})")
    if dev.storage:
        print(f"  Storage: {dev.storage.used_bytes / (1024**3):.2f} GB used of {dev.storage.total_bytes / (1024**3):.2f} GB")
```

## Running Unit Tests:
```bash
python -m unittest shared.discovery.test_detector
```
