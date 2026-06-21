"""
Unit tests for the Hardened CSV Exporter module
"""

import csv
import os
import tempfile
import unittest
from shared.discovery.detector import AndroidDevice, StorageInfo
from shared.inventory.manager import AppInfo
from .csv_exporter import CsvExporter


class TestCsvExporter(unittest.TestCase):

    def setUp(self):
        """Creates a secure temporary directory container for test outputs."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.exporter = CsvExporter(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_output_dir_auto_creation(self):
        """
        Verify the class creates target folders on initialization if they are missing.
        """
        nested_dir = os.path.join(self.test_dir.name, "nested", "reports")
        self.assertFalse(os.path.exists(nested_dir))
        
        CsvExporter(nested_dir)
        self.assertTrue(os.path.exists(nested_dir))

    def test_export_device_info_writes_file_successfully(self):
        """
        Verify key-value device metadata compiles with correct byte calculations.
        """
        storage = StorageInfo(
            total_bytes=10 * (1024**3),
            used_bytes=8 * (1024**3),
            free_bytes=2 * (1024**3)
        )
        device = AndroidDevice(
            serial="serial-123",
            status="device",
            manufacturer="Samsung",
            model="S23",
            android_version="14",
            api_level=34,
            storage=storage
        )

        out_path = self.exporter.export_device_info("device_report.csv", device)
        self.assertTrue(os.path.exists(out_path))

        # Open with utf-8-sig to verify BOM decoding is smooth
        with open(out_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)

        self.assertEqual(rows[0], ["Metric", "Value"])
        self.assertEqual(rows[1], ["Device Serial", "serial-123"])
        self.assertEqual(rows[7], ["Total Storage Space", "10.00 GB"])

    def test_csv_formula_injection_sanitization(self):
        """
        Verify cells beginning with formula control chars (=, +, -, @) are prepended with a single quote.
        """
        apps = [
            AppInfo(
                app_name="=calc()", # Dangerous formula name
                package_name="com.dangerous.app",
                version_name="+1.0", # Dangerous version
                version_code=1,
                apk_path="@system/app", # Dangerous path
                is_system=False
            )
        ]

        out_path = self.exporter.export_app_inventory("threat_inventory.csv", apps)
        self.assertTrue(os.path.exists(out_path))

        with open(out_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Formula chars must be neutralized
        self.assertEqual(rows[1][0], "'=calc()")
        self.assertEqual(rows[1][2], "'+1.0")
        self.assertEqual(rows[1][4], "'@system/app")

    def test_filename_sanitization_prevents_traversal(self):
        """
        Verify traversal paths are stripped from filename variables.
        """
        malicious_input = "../../../../etc/passwd.csv"
        sanitized = self.exporter._sanitize_filename(malicious_input)
        self.assertEqual(sanitized, "passwd.csv")

        bad_chars = "device:*?<>|info.csv"
        sanitized_chars = self.exporter._sanitize_filename(bad_chars)
        # Illegal characters replaced by underscores
        self.assertEqual(sanitized_chars, "device______info.csv")

    @unittest.mock.patch("os.replace")
    def test_file_lock_permission_error_handling(self, mock_replace):
        """
        Verify that locked destination files raise a descriptive IOError (DEF-101).
        """
        mock_replace.side_effect = PermissionError("File locked by Excel")
        
        with self.assertRaises(IOError) as ctx:
            self.exporter.export_app_inventory("locked.csv", [])
            
        self.assertIn("Permission denied", str(ctx.exception))
        self.assertIn("is currently locked", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
