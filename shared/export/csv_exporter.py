"""
Phoenix Backup CSV Export Module (Hardened Python Implementation)
"""

import csv
import logging
import os
import re
import tempfile
from typing import List, Any
from shared.discovery.detector import AndroidDevice
from shared.inventory.manager import AppInfo

# Configure module-level logger
logger = logging.getLogger("phoenix.export")

class CsvExporter:
    """
    Service responsible for compiling device metadata and application lists
    into standardized CSV reports. Features CSV Injection sanitizations
    and atomic file writes.
    """

    def __init__(self, output_dir: str):
        """
        Initializes the exporter with a target output directory.
        Creates the folder if it does not exist.
        """
        self.output_dir = os.path.abspath(output_dir)
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            logger.info("CSV exporter initialized with output directory: %s", self.output_dir)
        except OSError as err:
            logger.error("Failed to create output directory '%s': %s", self.output_dir, err)
            raise IOError(f"Could not initialize export directory: {err}")

    def export_device_info(self, filename: str, device: AndroidDevice) -> str:
        """
        Compiles device details and partition capacities into a key-value CSV file.
        Returns the absolute filepath of the generated report. Writes atomically.
        """
        sanitized_filename = self._sanitize_filename(filename)
        target_path = os.path.join(self.output_dir, sanitized_filename)
        
        logger.info("Exporting device metadata for [%s] to: %s", device.serial, target_path)

        total_gb = f"{device.storage.total_bytes / (1024**3):.2f} GB" if device.storage else "N/A"
        used_gb = f"{device.storage.used_bytes / (1024**3):.2f} GB" if device.storage else "N/A"
        free_gb = f"{device.storage.free_bytes / (1024**3):.2f} GB" if device.storage else "N/A"

        rows = [
            ["Metric", "Value"],
            ["Device Serial", device.serial],
            ["Status", device.status],
            ["Manufacturer", device.manufacturer or "N/A"],
            ["Model", device.model or "N/A"],
            ["Android Version", device.android_version or "N/A"],
            ["API Level", str(device.api_level) if device.api_level else "N/A"],
            ["Total Storage Space", total_gb],
            ["Used Storage Space", used_gb],
            ["Free Storage Space", free_gb]
        ]

        # Apply CSV injection sanitizations to all output cell values
        sanitized_rows = [[self._sanitize_cell(cell) for cell in row] for row in rows]

        # Execute atomic write using temporary file replacement
        self._write_atomically(target_path, sanitized_rows)
        return target_path

    def export_app_inventory(self, filename: str, apps: List[AppInfo]) -> str:
        """
        Compiles the audited package lists into a tabular CSV report.
        Returns the absolute filepath of the generated report. Writes atomically.
        """
        sanitized_filename = self._sanitize_filename(filename)
        target_path = os.path.join(self.output_dir, sanitized_filename)
        
        logger.info("Exporting %d applications to: %s", len(apps), target_path)

        headers = ["App Name", "Package Name", "Version Name", "Version Code", "APK Path", "Is System"]
        rows = [headers]

        for app in apps:
            rows.append([
                app.app_name,
                app.package_name,
                app.version_name or "N/A",
                str(app.version_code) if app.version_code is not None else "N/A",
                app.apk_path,
                "Yes" if app.is_system else "No"
            ])

        # Apply CSV injection sanitizations
        sanitized_rows = [[self._sanitize_cell(cell) for cell in row] for row in rows]

        # Execute atomic write
        self._write_atomically(target_path, sanitized_rows)
        return target_path

    def _write_atomically(self, target_path: str, rows: List[List[str]]) -> None:
        """
        Helper method writing CSV rows atomically via a temp file.
        Uses utf-8-sig to inject the UTF-8 BOM so Excel decodes non-ASCII chars correctly.
        """
        dir_name = os.path.dirname(target_path)
        temp_path = None
        
        try:
            # Create a temporary file in the same directory to guarantee atomic move (same partition)
            with tempfile.NamedTemporaryFile(mode="w", dir=dir_name, delete=False, suffix=".tmp", encoding="utf-8-sig", newline="") as temp_file:
                temp_path = temp_file.name
                writer = csv.writer(temp_file)
                writer.writerows(rows)
            
            # Atomic rename replacement
            os.replace(temp_path, target_path)
            logger.debug("Atomic file commit completed at: %s", target_path)
        except (PermissionError, OSError) as lock_err:
            # Handle Windows file locks specifically, preventing raw crashes (DEF-101)
            logger.error("File lock encountered during CSV commit to '%s': %s", target_path, lock_err)
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise IOError(
                f"Permission denied: The report file '{os.path.basename(target_path)}' "
                "is currently locked. Please close any application holding it open "
                "(such as Excel) and try again."
            )
        except Exception as err:
            logger.error("Failed to commit CSV data atomically: %s", err)
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise IOError(f"Atomic file transaction failed: {err}")

    def _sanitize_cell(self, cell: Any) -> str:
        """
        Sanitizes cell contents to prevent CSV / Excel Formula Injection vulnerabilities.
        Neutralizes formula execution characters (=, +, -, @) by prepending a single quote.
        """
        val_str = str(cell) if cell is not None else ""
        if val_str and val_str[0] in ("=", "+", "-", "@"):
            logger.warning("Sanitized potential CSV Injection value: '%s'", val_str)
            return f"'{val_str}"
        return val_str

    def _sanitize_filename(self, filename: str) -> str:
        """
        Filters input characters to prevent directory traversal or malformed files errors.
        """
        base = os.path.basename(filename)
        sanitized = re.sub(r"[^\w\.\-]", "_", base)
        if not sanitized.lower().endswith(".csv"):
            sanitized += ".csv"
        return sanitized
