"""
Integration tests for the MVP Orchestration Flow
"""

import csv
import os
import tempfile
import unittest
from unittest.mock import MagicMock
from shared.adb.wrapper import AdbDevice
from shared.db.connection import DatabaseConnectionManager
from shared.db.migrations import MigrationRunner
from shared.db.repositories import DeviceRepository, BackupJobRepository, AuditLogRepository
from .flow import MvpOrchestrator


class TestMvpOrchestratorIntegration(unittest.TestCase):

    def setUp(self):
        """Sets up a temporary file DB, runs migrations, and creates temp folder for CSVs."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_manager = DatabaseConnectionManager(self.temp_db.name)
        
        # Apply SQLite migrations
        with self.db_manager.get_connection() as conn:
            runner = MigrationRunner(conn)
            runner.run_migrations()

        self.test_dir = tempfile.TemporaryDirectory()
        self.mock_adb = MagicMock()

    def tearDown(self):
        self.test_dir.cleanup()
        os.unlink(self.temp_db.name)

    def test_complete_audit_flow_execution_success(self):
        """
        Verify the entire pipeline runs and records transactions successfully.
        """
        serial = "emulator-5554"
        
        # 1. Mock adb list devices response (device is connected and active)
        self.mock_adb.list_devices.return_value = [
            AdbDevice(serial=serial, status="device", model="Pixel 6")
        ]
        
        # 2. Mock adb getprop metadata
        mock_properties = {
            (serial, "ro.product.manufacturer"): "Google",
            (serial, "ro.product.model"): "Pixel 6",
            (serial, "ro.build.version.release"): "13",
            (serial, "ro.build.version.sdk"): "33"
        }
        self.mock_adb.get_device_property.side_effect = lambda s, prop: mock_properties.get((s, prop))
        
        # 3. Mock stat query output for storage capacity checks
        self.mock_adb.execute_shell_command.side_effect = [
            "1000|200|4096\n", # stat output
            "package:/data/app/com.whatsapp/base.apk=com.whatsapp\n", # pm list output
            "versionName=2.24.10\nversionCode=241076000\n" # pm dump output
        ]

        # Initialize orchestrator
        orchestrator = MvpOrchestrator(
            db_manager=self.db_manager,
            adb_client=self.mock_adb,
            output_dir=self.test_dir.name
        )

        # Execute the pipeline
        success = orchestrator.execute_migration_audit(serial)
        self.assertTrue(success)

        # --- SQLite Database Assertions ---
        with self.db_manager.get_connection(read_only=True) as conn:
            device_repo = DeviceRepository(conn)
            job_repo = BackupJobRepository(conn)
            audit_repo = AuditLogRepository(conn)

            # Assert device record exists in SQLite
            device = device_repo.get_device(serial)
            self.assertIsNotNone(device)
            self.assertEqual(device["manufacturer"], "Google")
            self.assertEqual(device["model"], "Pixel 6")

            # Assert backup job status is COMPLETED and readiness score is written
            # Query the latest job (since job_id is random uuid)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM backup_jobs WHERE device_id = ?;", (serial,))
            job = cursor.fetchone()
            self.assertIsNotNone(job)
            self.assertEqual(job["status"], "COMPLETED")
            self.assertEqual(job["readiness_score"], 100)

            # Assert audit log records were written
            logs = audit_repo.get_recent_logs()
            self.assertGreater(len(logs), 0)
            self.assertEqual(logs[0]["module"], "ORCHESTRATOR")
            self.assertIn("completed", logs[0]["message"])

        # --- CSV Export Assertions ---
        device_csv_path = os.path.join(self.test_dir.name, f"device_summary_{serial}.csv")
        apps_csv_path = os.path.join(self.test_dir.name, f"apps_inventory_{serial}.csv")

        self.assertTrue(os.path.exists(device_csv_path))
        self.assertTrue(os.path.exists(apps_csv_path))

        # Assert Device CSV Content
        with open(device_csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            device_rows = list(reader)
        self.assertEqual(device_rows[1], ["Device Serial", serial])
        self.assertEqual(device_rows[3], ["Manufacturer", "Google"])

        # Assert Applications CSV Content
        with open(apps_csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            apps_rows = list(reader)
        self.assertEqual(apps_rows[0], ["App Name", "Package Name", "Version Name", "Version Code", "APK Path", "Is System"])
        self.assertEqual(apps_rows[1], ["Whatsapp", "com.whatsapp", "2.24.10", "241076000", "/data/app/com.whatsapp/base.apk", "No"])


if __name__ == "__main__":
    unittest.main()
