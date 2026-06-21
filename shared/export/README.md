# CSV Exporter Module - Phoenix Backup

This module is responsible for compiling device information and application inventory lists into standardized CSV files.

## Features:
1.  **Tabular Reports Exporter:**
    *   `export_device_info`: Compiles device properties (Serial, model, API, storage capacities in GB) into a structured key-value format CSV.
    *   `export_app_inventory`: Compiles the parsed application array into a tabular format CSV (`App Name`, `Package Name`, `Version Name`, `Version Code`, `APK Path`, `Is System`).
2.  **Configurable Output Targets:** Automatically creates output paths on initialization (`os.makedirs`).
3.  **Cross-Platform Newline Safety:** Uses Python `newline=""` to prevent double spacing blank-line injections on Windows host OS.
4.  **Security Sanitization:** Strips path navigation identifiers (`../`) and illegal character sets to prevent local path traversal.

## Usage:
```python
from shared.discovery.detector import AndroidDevice, StorageInfo
from shared.export.csv_exporter import CsvExporter

# Initialize exporter targeting local output directory
exporter = CsvExporter(output_dir="./reports")

# Setup device details
storage = StorageInfo(total_bytes=64*1024**3, used_bytes=32*1024**3, free_bytes=32*1024**3)
device = AndroidDevice(
    serial="serial-123",
    status="device",
    manufacturer="Google",
    model="Pixel 6",
    android_version="14",
    api_level=34,
    storage=storage
)

# Export reports
exporter.export_device_info(filename="device_summary.csv", device=device)
```

## Running Unit Tests:
```bash
python -m unittest shared.export.test_exporter
```
