"""
Integration tests for the Sprint 2 Orchestrator Flow
"""

import os
import json
import tempfile
import unittest
from unittest.mock import MagicMock
from shared.db.connection import DatabaseConnectionManager
from shared.db.migrations import MigrationRunner
from shared.db.repositories import DeviceRepository, AppInventoryRepository, StorageManifestRepository
from shared.intelligence.rules import RiskKnowledgeBaseLoader
from shared.orchestrator.sprint2_flow import Sprint2Orchestrator
from shared.adb.wrapper import AdbDevice

class TestSprint2Orchestrator(unittest.TestCase):

    def setUp(self):
        # Temp Database Setup
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_manager = DatabaseConnectionManager(self.temp_db.name)

        # Apply database migrations
        with self.db_manager.get_connection() as conn:
            runner = MigrationRunner(conn)
            runner.run_migrations()

        # Rules Config Setup
        self.temp_rules = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json", encoding="utf-8")
        self.rules_data = [
            {
                "package_pattern": "com.google.android.apps.authenticator2",
                "app_name": "Google Authenticator",
                "category": "AUTHENTICATOR",
                "severity": "CRITICAL",
                "reasoning": "Local Keystore dependency.",
                "remediation": "Export credentials via manual QR code."
            },
            {
                "package_pattern": "com.example.bank",
                "app_name": "Example Bank",
                "category": "BANKING",
                "severity": "HIGH",
                "reasoning": "Financial app bound to device ID.",
                "remediation": "Confirm banking credentials and SMS access."
            }
        ]
        json.dump(self.rules_data, self.temp_rules)
        self.temp_rules.close()

        self.rules_loader = RiskKnowledgeBaseLoader(self.temp_rules.name)

        # Output Dir Setup
        self.temp_output_dir = tempfile.TemporaryDirectory()

        # Mock ADB Client Setup
        self.mock_adb = MagicMock()
        self.serial = "demo-device-123"

        # Mock list_devices
        self.mock_adb.list_devices.return_value = [
            AdbDevice(serial=self.serial, status="device", model="Pixel 6")
        ]

        # Mock properties
        def get_prop(serial, prop_name):
            if prop_name == "ro.product.model":
                return "Pixel 6"
            if prop_name == "ro.build.version.sdk":
                return "31" # Android 12
            return None
        self.mock_adb.get_device_property.side_effect = get_prop

        # Mock shell commands
        def exec_shell(serial, command, args=None, timeout=15):
            args = args or []
            if command == "pm" and "list" in args and "packages" in args:
                return (
                    "package:/data/app/com.google.android.apps.authenticator2/base.apk=com.google.android.apps.authenticator2\n"
                    "package:/data/app/com.example.bank/base.apk=com.example.bank\n"
                    "package:/data/app/com.example.social/base.apk=com.example.social\n"
                )
            if command == "dumpsys" and "package" in args:
                pkg = args[1]
                if pkg == "com.example.bank":
                    # Simulates bank app having ALLOW_BACKUP flag in manifest
                    return "  flags=[ HAS_CODE ALLOW_BACKUP ]"
                if pkg == "com.google.android.apps.authenticator2":
                    # Simulates authenticator missing ALLOW_BACKUP
                    return "  flags=[ HAS_CODE ]"
            if command == "du":
                path = args[-1]
                if path == "/sdcard/DCIM":
                    return "100000\t/sdcard/DCIM" # ~100MB
                if path == "/sdcard/Pictures":
                    return "50000\t/sdcard/Pictures" # ~50MB
                return "0\t" + path
            return ""

        self.mock_adb.execute_shell_command.side_effect = exec_shell

    def tearDown(self):
        os.unlink(self.temp_db.name)
        os.unlink(self.temp_rules.name)
        self.temp_output_dir.cleanup()

    def test_sprint2_orchestration_e2e(self):
        orchestrator = Sprint2Orchestrator(
            db_manager=self.db_manager,
            adb_client=self.mock_adb,
            rules_loader=self.rules_loader,
            output_dir=self.temp_output_dir.name
        )

        # Run E2E pipeline
        assessment = orchestrator.execute_migration_audit(
            serial=self.serial,
            user_overrides=["com.example.bank"] # Acknowledge bank risks
        )

        # Assertions
        self.assertIsNotNone(assessment)
        self.assertGreater(assessment.readiness_score, 0)
        self.assertTrue(os.path.exists(os.path.join(self.temp_output_dir.name, "recovery_analysis.json")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_output_dir.name, "recovery_readiness_report.html")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_output_dir.name, "recovery_readiness_report.pdf")))

        # Check SQLite db updates
        with self.db_manager.get_connection() as conn:
            app_repo = AppInventoryRepository(conn)
            storage_repo = StorageManifestRepository(conn)

            # Check that 3 apps were saved
            db_apps = app_repo.get_apps_for_device(self.serial)
            self.assertEqual(len(db_apps), 3)

            # Google Authenticator (Critical risk)
            auth_app = next(a for a in db_apps if a["package_name"] == "com.google.android.apps.authenticator2")
            self.assertEqual(auth_app["allow_backup"], 0) # blocked
            self.assertEqual(auth_app["backup_source"], "RULE_MATCH")

            # Example Bank (High risk, but dumpsys has ALLOW_BACKUP -> Overridden to False because SDK 31)
            # Wait, our logic says: on API 31+ user apps are allowBackup=False due to Android 12+ system blocks.
            bank_app = next(a for a in db_apps if a["package_name"] == "com.example.bank")
            self.assertEqual(bank_app["allow_backup"], 0)
            self.assertEqual(bank_app["backup_source"], "RULE_MATCH")

            # Example Social (API 31 user app -> defaults to False)
            social_app = next(a for a in db_apps if a["package_name"] == "com.example.social")
            self.assertEqual(social_app["allow_backup"], 0)
            self.assertEqual(social_app["backup_source"], "HEURISTIC_API")

            # Verify storage manifests
            storage_manifests = storage_repo.get_storage_manifest_for_device(self.serial)
            self.assertEqual(len(storage_manifests), 4) # DCIM, Pictures, Documents, Download
            dcim_manifest = next(m for m in storage_manifests if m["directory_path"] == "/sdcard/DCIM")
            self.assertEqual(dcim_manifest["total_bytes"], 100000 * 1024)

if __name__ == "__main__":
    unittest.main()
