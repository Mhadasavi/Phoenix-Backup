"""
Phoenix Backup Sprint 2 Acceptance Tests
"""

import os
import json
import tempfile
import unittest
from unittest.mock import MagicMock

from shared.db.connection import DatabaseConnectionManager
from shared.db.migrations import MigrationRunner
from shared.db.repositories import AppInventoryRepository, StorageManifestRepository
from shared.intelligence.rules import RiskKnowledgeBaseLoader
from shared.orchestrator.sprint2_flow import Sprint2Orchestrator
from shared.adb.wrapper import AdbDevice
from shared.intelligence.scoring import RecoveryReadinessCalculator, RiskScoreCalculator

class TestSprint2Acceptance(unittest.TestCase):

    def setUp(self):
        # Temp files & DB setup
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_manager = DatabaseConnectionManager(self.temp_db.name)

        with self.db_manager.get_connection() as conn:
            MigrationRunner(conn).run_migrations()

        # Temp Rules config
        self.temp_rules = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json", encoding="utf-8")
        self.rules_data = [
            {
                "package_pattern": "com.google.android.apps.authenticator2",
                "app_name": "Google Authenticator",
                "category": "AUTHENTICATOR",
                "severity": "CRITICAL",
                "reasoning": "Bound to device keystore.",
                "remediation": "Export QR codes manually."
            }
        ]
        json.dump(self.rules_data, self.temp_rules)
        self.temp_rules.close()
        self.rules_loader = RiskKnowledgeBaseLoader(self.temp_rules.name)

        self.temp_output_dir = tempfile.TemporaryDirectory()
        self.mock_adb = MagicMock()
        self.serial = "acceptance-device"
        self.mock_adb.list_devices.return_value = [AdbDevice(self.serial, "device", "Test Phone")]

    def tearDown(self):
        os.unlink(self.temp_db.name)
        os.unlink(self.temp_rules.name)
        self.temp_output_dir.cleanup()

    def test_acceptance_adr001_layered_allow_backup(self):
        """
        Verify ADR 001: Layered Resolution (Rule Match, API Heuristics, Dumpsys Fallback)
        """
        # Scenario: Android 12 (SDK 31) Device.
        # 1. Unknown app (com.example.social) -> should default allow_backup to False via Heuristics
        # 2. Rule matched app (com.google.android.apps.authenticator2) -> should resolve to RULE_MATCH
        # 3. High-risk unknown app (com.unknown.bank) -> should invoke dumpsys fallback
        
        def get_prop(serial, prop_name):
            if prop_name == "ro.product.model": return "Test Phone"
            if prop_name == "ro.build.version.sdk": return "31" # Android 12
            return None
        self.mock_adb.get_device_property.side_effect = get_prop

        def exec_shell(serial, command, args=None, timeout=15):
            args = args or []
            if command == "pm" and "list" in args:
                return (
                    "package:/data/app/com.google.android.apps.authenticator2/base.apk=com.google.android.apps.authenticator2\n"
                    "package:/data/app/com.example.social/base.apk=com.example.social\n"
                    "package:/data/app/com.unknown.bank/base.apk=com.unknown.bank\n"
                )
            if command == "dumpsys" and "package" in args:
                pkg = args[1]
                if pkg == "com.unknown.bank":
                    return "  flags=[ HAS_CODE ALLOW_BACKUP ]" # dumpsys finds allowBackup=true
                return "  flags=[ HAS_CODE ]"
            if command == "du":
                return "0\t" + args[-1]
            return ""
        self.mock_adb.execute_shell_command.side_effect = exec_shell

        orchestrator = Sprint2Orchestrator(
            db_manager=self.db_manager,
            adb_client=self.mock_adb,
            rules_loader=self.rules_loader,
            output_dir=self.temp_output_dir.name
        )

        orchestrator.execute_migration_audit(serial=self.serial)

        with self.db_manager.get_connection() as conn:
            app_repo = AppInventoryRepository(conn)
            apps = app_repo.get_apps_for_device(self.serial)

            # Assert 1: com.example.social is user app on SDK 31 -> Heuristic blocks it
            social = next(a for a in apps if a["package_name"] == "com.example.social")
            self.assertEqual(social["allow_backup"], 0)
            self.assertEqual(social["backup_source"], "HEURISTIC_API")

            # Assert 2: com.google.android.apps.authenticator2 is rule matched
            auth = next(a for a in apps if a["package_name"] == "com.google.android.apps.authenticator2")
            self.assertEqual(auth["allow_backup"], 0)
            self.assertEqual(auth["backup_source"], "RULE_MATCH")

            # Assert 3: com.unknown.bank is high risk and has ALLOW_BACKUP in dumpsys.
            # But because it's SDK 31 third-party, it overrides to False, source is DUMPSYS_RESOLVED
            bank = next(a for a in apps if a["package_name"] == "com.unknown.bank")
            self.assertEqual(bank["allow_backup"], 0)
            self.assertEqual(bank["backup_source"], "DUMPSYS_RESOLVED")

    def test_acceptance_adr002_storage_sync_metrics(self):
        """
        Verify ADR 002: Storage Sync Sizing & Sync Ratio Calculation
        """
        def get_prop(serial, prop_name):
            if prop_name == "ro.product.model": return "Test Phone"
            if prop_name == "ro.build.version.sdk": return "29" # Android 10
            return None
        self.mock_adb.get_device_property.side_effect = get_prop

        def exec_shell(serial, command, args=None, timeout=15):
            args = args or []
            if command == "pm" and "list" in args:
                return "package:/data/app/com.example.social/base.apk=com.example.social\n"
            if command == "du":
                path = args[-1]
                if path == "/sdcard/DCIM": return "1000\t/sdcard/DCIM" # 1000 KB -> 1,024,000 bytes
                return "0\t" + path
            return ""
        self.mock_adb.execute_shell_command.side_effect = exec_shell

        # Setup host-side files under target output dir/sync/DCIM (Pass 2)
        sync_dir = os.path.join(self.temp_output_dir.name, "sync", "DCIM")
        os.makedirs(sync_dir, exist_ok=True)
        # Create a mock local file of 512KB (50% sync)
        with open(os.path.join(sync_dir, "pic.jpg"), "wb") as f:
            f.write(b"\0" * 512 * 1024)

        orchestrator = Sprint2Orchestrator(
            db_manager=self.db_manager,
            adb_client=self.mock_adb,
            rules_loader=self.rules_loader,
            output_dir=self.temp_output_dir.name
        )

        orchestrator.execute_migration_audit(serial=self.serial)

        with self.db_manager.get_connection() as conn:
            storage_repo = StorageManifestRepository(conn)
            manifests = storage_repo.get_storage_manifest_for_device(self.serial)
            
            dcim = next(m for m in manifests if m["directory_path"] == "/sdcard/DCIM")
            self.assertEqual(dcim["total_bytes"], 1024000)
            self.assertEqual(dcim["synced_bytes"], 524288) # Exactly 512KB

    def test_acceptance_readiness_formula(self):
        """
        Verify the mathematical scoring readiness score and limits
        """
        # Test bounds of scoring calculator directly
        # Max core score is 45, max storage is 55. Total is 100.
        score_perfect = RecoveryReadinessCalculator.calculate_readiness_score(
            has_contacts=True,
            has_sms=True,
            has_call_logs=True,
            is_tablet=False,
            total_storage_bytes=1000,
            synced_storage_bytes=1000,
            unresolved_penalties=[]
        )
        self.assertEqual(score_perfect, 100)

        # Test tablet profile override (no SMS/calls, weights redistribution)
        # Max core score is 45, max storage is 55. Contacts is 45.
        score_tablet = RecoveryReadinessCalculator.calculate_readiness_score(
            has_contacts=True,
            has_sms=False,
            has_call_logs=False,
            is_tablet=True,
            total_storage_bytes=1000,
            synced_storage_bytes=500, # 50% storage sync -> 27.5 score
            unresolved_penalties=[]
        )
        # Contacts = 45. Storage = 50% of 55 = 27.5 -> rounded to 27 -> Total = 72
        self.assertEqual(score_tablet, 72)

        # Clamping checks
        score_negative = RecoveryReadinessCalculator.calculate_readiness_score(
            has_contacts=False,
            has_sms=False,
            has_call_logs=False,
            is_tablet=False,
            total_storage_bytes=100,
            synced_storage_bytes=0,
            unresolved_penalties=[100, 20]
        )
        self.assertEqual(score_negative, 0) # must clamp to [0, 100]

    def test_acceptance_json_report_export(self):
        """
        Verify that recovery_analysis.json is correctly formatted
        """
        def get_prop(serial, prop_name):
            if prop_name == "ro.product.model": return "Test Phone"
            if prop_name == "ro.build.version.sdk": return "30"
            return None
        self.mock_adb.get_device_property.side_effect = get_prop

        def exec_shell(serial, command, args=None, timeout=15):
            args = args or []
            if command == "pm" and "list" in args:
                return "package:/data/app/com.google.android.apps.authenticator2/base.apk=com.google.android.apps.authenticator2\n"
            if command == "du":
                return "0\t" + args[-1]
            return ""
        self.mock_adb.execute_shell_command.side_effect = exec_shell

        orchestrator = Sprint2Orchestrator(
            db_manager=self.db_manager,
            adb_client=self.mock_adb,
            rules_loader=self.rules_loader,
            output_dir=self.temp_output_dir.name
        )

        orchestrator.execute_migration_audit(serial=self.serial)
        
        report_file = os.path.join(self.temp_output_dir.name, "recovery_analysis.json")
        self.assertTrue(os.path.exists(report_file))

        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("readiness_score", data)
        self.assertIn("readiness_state", data)
        self.assertIn("verdicts", data)
        self.assertIn("findings", data)
        self.assertIn("checklist", data)
        self.assertIn("inventory", data)

if __name__ == "__main__":
    unittest.main()
