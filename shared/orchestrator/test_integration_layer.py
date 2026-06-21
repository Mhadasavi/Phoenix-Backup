"""
Integration tests for the Sprint 2 System Integration Layer
"""

import unittest
import os
import shutil
import tempfile
import json
from unittest.mock import MagicMock
from shared.db.connection import DatabaseConnectionManager
from shared.db.migrations import MigrationRunner
from shared.db.repositories import BackupJobRepository, JobAppInventoryRepository
from shared.adb.wrapper import AdbClientInterface, AdbDevice
from shared.intelligence.classifier import UnknownAppClassifier
from shared.intelligence.findings import FindingsEngine
from shared.intelligence.rules import RiskKnowledgeBaseLoader, ApplicationClassifier
from shared.intelligence.recommendation import RecoveryRecommendationEngine
from shared.export.html_exporter import HtmlReportEngine
from shared.export.pdf_exporter import PdfReportGenerator
from shared.orchestrator.integration import Sprint2SystemIntegrator


class MockIntegrationAdb(AdbClientInterface):
    """Mock ADB client yielding realistic package scans and permissions."""

    def __init__(self, serial: str):
        self.serial = serial

    def is_adb_available(self) -> bool:
        return True

    def list_devices(self) -> list:
        return [AdbDevice(serial=self.serial, status="device", model="Pixel 7 Pro")]

    def get_device_property(self, serial: str, property_name: str) -> str:
        if property_name == "ro.product.model":
            return "Pixel 7 Pro"
        if property_name == "ro.build.version.sdk":
            return "33"
        return "Unknown"

    def execute_shell_command(self, serial: str, command: str, args: list = None) -> str:
        args = args or []
        if command == "pm" and "list" in args:
            return (
                "package:/data/app/com.google.android.apps.authenticator2/base.apk=com.google.android.apps.authenticator2\n"
                "package:/data/app/com.x8bit.bitwarden/base.apk=com.x8bit.bitwarden\n"
                "package:/data/app/xyz.retro.game/base.apk=xyz.retro.game\n"
            )
        if command == "pm" and "dump" in args:
            # Package permissions dump
            pkg = args[1]
            if pkg == "com.google.android.apps.authenticator2":
                return "requested permissions:\n  android.permission.CAMERA\n  android.permission.USE_BIOMETRIC\n"
            if pkg == "com.x8bit.bitwarden":
                return "requested permissions:\n  android.permission.USE_BIOMETRIC\n  android.permission.INTERNET\n"
            return "requested permissions:\n  android.permission.VIBRATE\n"

        if command == "dumpsys" and "package" in args:
            pkg = args[1]
            if pkg == "com.google.android.apps.authenticator2":
                return "  flags=[ HAS_CODE ALLOW_BACKUP ]"
            if pkg == "com.x8bit.bitwarden":
                return "  flags=[ HAS_CODE ALLOW_BACKUP ]"
            return "  flags=[ HAS_CODE ]"

        if command == "du":
            return "500000\t" + args[-1]

        return ""


class TestSprint2SystemIntegrator(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_file = os.path.join(self.temp_dir, "test_integration.db")
        self.db_manager = DatabaseConnectionManager(self.db_file)

        # Run DDL migrations
        with self.db_manager.get_connection() as conn:
            runner = MigrationRunner(conn)
            runner.run_migrations()

        self.serial = "integration-device-123"
        self.adb_client = MockIntegrationAdb(self.serial)

        # Build Rules & Exporters
        self.rules_loader = RiskKnowledgeBaseLoader()
        rules = self.rules_loader.load_rules()
        self.app_classifier = ApplicationClassifier(rules)

        self.classifier = UnknownAppClassifier()
        self.findings_engine = FindingsEngine(self.app_classifier)
        self.recommendation_engine = RecoveryRecommendationEngine(self.classifier)
        
        self.html_exporter = HtmlReportEngine()
        self.pdf_exporter = PdfReportGenerator(self.temp_dir)

        self.integrator = Sprint2SystemIntegrator(
            db_manager=self.db_manager,
            adb_client=self.adb_client,
            classifier=self.classifier,
            findings_engine=self.findings_engine,
            recommendation_engine=self.recommendation_engine,
            html_exporter=self.html_exporter,
            pdf_exporter=self.pdf_exporter,
            output_dir=self.temp_dir
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_execute_system_audit_happy_path(self):
        # Run audit with no overrides
        result = self.integrator.execute_system_audit(serial=self.serial, user_overrides=[])

        self.assertIsNotNone(result)
        self.assertEqual(result["findings_count"], 2) # Authenticator + Password Manager are high risk
        self.assertGreater(result["readiness_score"], 0)
        self.assertIn(result["readiness_state"], ("WARNING", "CRITICAL_UNPREPARED"))

        # Verify output files exist
        analysis_json_path = os.path.join(self.temp_dir, "recovery_analysis.json")
        html_report_path = os.path.join(self.temp_dir, "recovery_readiness_report.html")
        pdf_report_path = os.path.join(self.temp_dir, "recovery_readiness_report.pdf")

        self.assertTrue(os.path.exists(analysis_json_path))
        self.assertTrue(os.path.exists(html_report_path))
        self.assertTrue(os.path.exists(pdf_report_path))

        # Check recovery sequence in JSON analysis file
        with open(analysis_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("recovery_sequence", data)
            self.assertGreater(len(data["recovery_sequence"]), 0)
            
            # Google Authenticator and Bitwarden must be in recovery actions
            actions = [a["action_id"] for a in data["recovery_sequence"]]
            self.assertTrue(any("com.google.android.apps.authenticator2" in aid for aid in actions))
            self.assertTrue(any("com.x8bit.bitwarden" in aid for aid in actions))

        # Verify historical snapshots saved to Database
        with self.db_manager.get_connection(read_only=True) as conn:
            job_app_repo = JobAppInventoryRepository(conn)
            apps = job_app_repo.get_apps_for_job(result["job_id"])
            self.assertEqual(len(apps), 3) # com.google.android.apps.authenticator2, com.x8bit.bitwarden, xyz.retro.game
            
            package_names = [a["package_name"] for a in apps]
            self.assertIn("com.google.android.apps.authenticator2", package_names)
            self.assertIn("com.x8bit.bitwarden", package_names)
            
            # Assert categories were classified historically
            auth_app = next(a for a in apps if a["package_name"] == "com.google.android.apps.authenticator2")
            self.assertEqual(auth_app["category"], "AUTHENTICATOR")
            self.assertEqual(auth_app["risk_score"], 100) # 80 base + 15 no backup + 5 API 33 penalty

    def test_execute_system_audit_crashed_exporter_gracefully_completes(self):
        # Force the PDF exporter to raise an error during generation
        mock_pdf_generator = MagicMock()
        mock_pdf_generator.generate_report.side_effect = PermissionError("File locked.")

        # Re-inject crashed exporter
        crashed_integrator = Sprint2SystemIntegrator(
            db_manager=self.db_manager,
            adb_client=self.adb_client,
            classifier=self.classifier,
            findings_engine=self.findings_engine,
            recommendation_engine=self.recommendation_engine,
            html_exporter=self.html_exporter,
            pdf_exporter=mock_pdf_generator,
            output_dir=self.temp_dir
        )

        # Execute system audit
        result = crashed_integrator.execute_system_audit(serial=self.serial, user_overrides=[])

        # Pipeline should NOT return None (it completes via try/except and updates DB to partial/complete)
        self.assertIsNotNone(result)
        self.assertIn("job_id", result)

        # Check DB status is COMPLETED or PARTIAL (not FAILED or crash-interrupted)
        with self.db_manager.get_connection(read_only=True) as conn:
            job_repo = BackupJobRepository(conn)
            job = job_repo.get_job(result["job_id"])
            self.assertIn(job["status"], ("COMPLETED", "PARTIAL"))


if __name__ == "__main__":
    unittest.main()
