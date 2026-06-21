"""
Phoenix Backup Sprint 2 System Integration End-to-End Acceptance Tests
"""

import os
import json
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

from shared.db.connection import DatabaseConnectionManager
from shared.db.migrations import MigrationRunner
from shared.db.repositories import (
    DeviceRepository,
    BackupJobRepository,
    AppInventoryRepository,
    StorageManifestRepository,
    JobAppInventoryRepository
)
from shared.adb.wrapper import AdbClientInterface, AdbDevice
from shared.intelligence.classifier import UnknownAppClassifier
from shared.intelligence.findings import FindingsEngine
from shared.intelligence.rules import RiskKnowledgeBaseLoader, ApplicationClassifier
from shared.intelligence.recommendation import RecoveryRecommendationEngine
from shared.export.html_exporter import HtmlReportEngine
from shared.export.pdf_exporter import PdfReportGenerator
from shared.orchestrator.integration import Sprint2SystemIntegrator


class MockAcceptanceAdb(AdbClientInterface):
    """Mock ADB client that provides controllable responses for acceptance tests."""

    def __init__(self, serial: str, model: str, sdk: str, status: str = "device"):
        self.serial = serial
        self.model = model
        self.sdk = sdk
        self.status = status
        self.shell_calls = 0

    def is_adb_available(self) -> bool:
        return True

    def list_devices(self) -> list:
        return [AdbDevice(serial=self.serial, status=self.status, model=self.model)]

    def get_device_property(self, serial: str, property_name: str) -> str:
        if serial != self.serial:
            return "Unknown"
        if property_name == "ro.product.model":
            return self.model
        if property_name == "ro.build.version.sdk":
            return self.sdk
        return "Unknown"

    def execute_shell_command(self, serial: str, command: str, args: list = None) -> str:
        self.shell_calls += 1
        args = args or []

        if command == "pm" and "list" in args:
            # Provide 3 applications: rule-based authenticator, unknown bank, unknown utility
            return (
                "package:/data/app/com.google.android.apps.authenticator2/base.apk=com.google.android.apps.authenticator2\n"
                "package:/data/app/com.someapp.bank/base.apk=com.someapp.bank\n"
                "package:/data/app/com.someapp.utility/base.apk=com.someapp.utility\n"
            )

        if command == "pm" and "dump" in args:
            # Package permissions dump
            pkg = args[1]
            if pkg == "com.google.android.apps.authenticator2":
                return "requested permissions:\n  android.permission.CAMERA\n  android.permission.USE_BIOMETRIC\n"
            if pkg == "com.someapp.bank":
                # Matches BANKING permissions
                return "requested permissions:\n  android.permission.INTERNET\n  android.permission.USE_BIOMETRIC\n"
            return "requested permissions:\n  android.permission.VIBRATE\n"

        if command == "dumpsys" and "package" in args:
            pkg = args[1]
            # Authenticator and bank explicitly support backup, utility does not
            if pkg in ("com.google.android.apps.authenticator2", "com.someapp.bank"):
                return "  flags=[ HAS_CODE ALLOW_BACKUP ]"
            return "  flags=[ HAS_CODE ]"

        if command == "du":
            # du -s -k <dir>
            # Let's say /sdcard/DCIM is 10000 KB (approx 10MB)
            path = args[-1]
            if path == "/sdcard/DCIM":
                return "10000\t/sdcard/DCIM"
            # /sdcard/Pictures is 5000 KB (approx 5MB)
            if path == "/sdcard/Pictures":
                return "5000\t/sdcard/Pictures"
            return "0\t" + path

        return ""


class TestSystemIntegrationAcceptance(unittest.TestCase):
    """Acceptance test suite enforcing the criteria for all 6 validation areas."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_file = os.path.join(self.temp_dir, "acceptance.db")
        self.db_manager = DatabaseConnectionManager(self.db_file)

        # Run database migrations
        with self.db_manager.get_connection() as conn:
            MigrationRunner(conn).run_migrations()

        # Build Rules & engines
        self.rules_loader = RiskKnowledgeBaseLoader()
        rules = self.rules_loader.load_rules()
        self.app_classifier = ApplicationClassifier(rules)

        self.classifier = UnknownAppClassifier()
        self.findings_engine = FindingsEngine(self.app_classifier)
        self.recommendation_engine = RecoveryRecommendationEngine(self.classifier)
        
        self.html_exporter = HtmlReportEngine()
        self.pdf_exporter = PdfReportGenerator(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_acceptance_flow_authorized_phone(self):
        """
        Validate E2E happy path for an authorized phone:
        1. Device Discovery
        2. Inventory Collection
        3. Risk Classification
        4. Recovery Readiness Score Calculation
        5. HTML Report Generation
        6. PDF Report Generation
        """
        serial = "acceptance-phone-123"
        model = "Acceptance Test Phone"
        sdk = "33"  # Android 13 (API 33)
        adb_client = MockAcceptanceAdb(serial=serial, model=model, sdk=sdk, status="device")

        # Setup local mock sync files under temp output dir to simulate local host storage check
        # /sdcard/DCIM is 10,240,000 bytes (10000 KB). Let's simulate 80% sync locally
        # 10000 * 1024 * 0.8 = 8,192,000 bytes
        dcim_sync_path = os.path.join(self.temp_dir, "sync", "DCIM")
        os.makedirs(dcim_sync_path, exist_ok=True)
        with open(os.path.join(dcim_sync_path, "photo.jpg"), "wb") as f:
            f.write(b"\0" * 8192000)

        # /sdcard/Pictures is 5,120,000 bytes (5000 KB). Let's simulate 50% sync locally
        # 5000 * 1024 * 0.5 = 2,560,000 bytes
        pics_sync_path = os.path.join(self.temp_dir, "sync", "Pictures")
        os.makedirs(pics_sync_path, exist_ok=True)
        with open(os.path.join(pics_sync_path, "pic.png"), "wb") as f:
            f.write(b"\0" * 2560000)

        integrator = Sprint2SystemIntegrator(
            db_manager=self.db_manager,
            adb_client=adb_client,
            classifier=self.classifier,
            findings_engine=self.findings_engine,
            recommendation_engine=self.recommendation_engine,
            html_exporter=self.html_exporter,
            pdf_exporter=self.pdf_exporter,
            output_dir=self.temp_dir
        )

        # Execute system audit pipeline
        result = integrator.execute_system_audit(serial=serial)

        # --- VALIDATION AREA 1: Device Discovery ---
        self.assertIsNotNone(result)
        self.assertIn("job_id", result)
        
        # Verify device record is persisted in DB
        with self.db_manager.get_connection(read_only=True) as conn:
            device_repo = DeviceRepository(conn)
            device = device_repo.get_device(serial)
            self.assertIsNotNone(device)
            self.assertEqual(device["model"], model)
            self.assertEqual(device["api_level"], 33)

        # --- VALIDATION AREA 2: Inventory Collection ---
        with self.db_manager.get_connection(read_only=True) as conn:
            app_repo = AppInventoryRepository(conn)
            apps = app_repo.get_apps_for_device(serial)
            self.assertEqual(len(apps), 3)
            
            packages = [a["package_name"] for a in apps]
            self.assertIn("com.google.android.apps.authenticator2", packages)
            self.assertIn("com.someapp.bank", packages)
            self.assertIn("com.someapp.utility", packages)

            # Check dynamic allowBackup resolutions:
            # - com.google.android.apps.authenticator2 is rule-matched, high risk. Resolves allow_backup=False on SDK 33
            auth_app = next(a for a in apps if a["package_name"] == "com.google.android.apps.authenticator2")
            self.assertEqual(auth_app["allow_backup"], 0)
            self.assertEqual(auth_app["backup_source"], "RULE_MATCH")

            # - com.someapp.bank is high risk (BANKING keyword). Dumpsys has ALLOW_BACKUP but overrides to False on SDK 33
            bank_app = next(a for a in apps if a["package_name"] == "com.someapp.bank")
            self.assertEqual(bank_app["allow_backup"], 0)
            self.assertEqual(bank_app["backup_source"], "DUMPSYS_RESOLVED")

        # --- VALIDATION AREA 3: Risk Classification ---
        # Verify historical job snapshots database contains resolved categories and risk scores
        with self.db_manager.get_connection(read_only=True) as conn:
            job_app_repo = JobAppInventoryRepository(conn)
            job_apps = job_app_repo.get_apps_for_job(result["job_id"])
            self.assertEqual(len(job_apps), 3)

            # 1. Predefined Rule Classification
            g_auth = next(a for a in job_apps if a["package_name"] == "com.google.android.apps.authenticator2")
            self.assertEqual(g_auth["category"], "AUTHENTICATOR")
            # Score: 80 base + 15 no backup + 5 API 33 = 100
            self.assertEqual(g_auth["risk_score"], 100)

            # 2. Unknown App Classification - Keyword Matches (BANKING)
            s_bank = next(a for a in job_apps if a["package_name"] == "com.someapp.bank")
            self.assertEqual(s_bank["category"], "BANKING")
            # Score: 85 base (unknown BANKING rule base) + 15 no backup + 5 API 33 = 105 -> clamped to 100
            self.assertEqual(s_bank["risk_score"], 100)

            # 3. Unknown App Classification - Fallback Matches
            s_util = next(a for a in job_apps if a["package_name"] == "com.someapp.utility")
            self.assertEqual(s_util["category"], "UNKNOWN_APP")
            # Score: 30 base + 15 no backup (utility doesn't support backup in dumpsys) = 45 (no API 33 penalty on unknown_app category)
            self.assertEqual(s_util["risk_score"], 45)

        # --- VALIDATION AREA 4: Recovery Readiness Calculation ---
        # Verify storage manifests populated (all 4 directories configured in logic: DCIM, Pictures, Documents, Download)
        with self.db_manager.get_connection(read_only=True) as conn:
            storage_repo = StorageManifestRepository(conn)
            manifests = storage_repo.get_storage_manifest_for_device(serial)
            self.assertEqual(len(manifests), 4)

            dcim_man = next(m for m in manifests if m["directory_path"] == "/sdcard/DCIM")
            self.assertEqual(dcim_man["total_bytes"], 10240000)
            self.assertEqual(dcim_man["synced_bytes"], 8192000)

            pics_man = next(m for m in manifests if m["directory_path"] == "/sdcard/Pictures")
            self.assertEqual(pics_man["total_bytes"], 5120000)
            self.assertEqual(pics_man["synced_bytes"], 2560000)

        # Readiness Math verification:
        # Base: has_contacts=True, has_sms=True, has_call_logs=True -> 15 + 15 + 15 = 45 points
        # Storage ratio: total = 10240000 + 5120000 = 15,360,000 bytes
        # Synced = 8192000 + 2560000 = 10,752,000 bytes
        # Ratio = 10752000 / 15360000 = 0.70
        # Storage Score = 0.70 * 55 = 38.5 -> int() = 38 points
        # Penalties:
        # - com.google.android.apps.authenticator2: Risk score 100 (CRITICAL) -> penalty 20 points
        # - com.someapp.bank: Risk score 100 (CRITICAL) -> penalty 20 points
        # - com.someapp.utility: Risk score 45 -> findings resets category to "Unknown" with severity LOW -> penalty 0
        # Total Penalties = 20 + 20 = 40 points
        # Score = (45 + 38) - 40 = 43 points.
        # Expected state is CRITICAL_UNPREPARED (score < 70)
        self.assertEqual(result["readiness_score"], 43)
        self.assertEqual(result["readiness_state"], "CRITICAL_UNPREPARED")

        # --- VALIDATION AREA 5: HTML Report Generation ---
        html_report_path = os.path.join(self.temp_dir, "recovery_readiness_report.html")
        self.assertTrue(os.path.exists(html_report_path))
        
        with open(html_report_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            self.assertIn("Recovery Readiness Report", html_content)
            self.assertIn(model, html_content)
            self.assertIn("com.google.android.apps.authenticator2", html_content)
            self.assertIn("com.someapp.bank", html_content)
            self.assertIn("CRITICAL", html_content)
            self.assertIn("43", html_content)

        # --- VALIDATION AREA 6: PDF Report Generation ---
        pdf_report_path = os.path.join(self.temp_dir, "recovery_readiness_report.pdf")
        self.assertTrue(os.path.exists(pdf_report_path))

        with open(pdf_report_path, "rb") as f:
            pdf_bytes = f.read(10)
            # PDF file header verification
            self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_acceptance_flow_unauthorized_device(self):
        """
        Verify that device discovery gracefully aborts if the device status is 'unauthorized'.
        """
        serial = "unauthorized-phone-123"
        model = "Unauthorized Phone"
        sdk = "33"
        # Status set to "unauthorized"
        adb_client = MockAcceptanceAdb(serial=serial, model=model, sdk=sdk, status="unauthorized")

        integrator = Sprint2SystemIntegrator(
            db_manager=self.db_manager,
            adb_client=adb_client,
            classifier=self.classifier,
            findings_engine=self.findings_engine,
            recommendation_engine=self.recommendation_engine,
            html_exporter=self.html_exporter,
            pdf_exporter=self.pdf_exporter,
            output_dir=self.temp_dir
        )

        result = integrator.execute_system_audit(serial=serial)
        # Should gracefully return None without raising exceptions or completing the job
        self.assertIsNone(result)

        # Verify no job status COMPLETED is written to database for this serial
        with self.db_manager.get_connection(read_only=True) as conn:
            job_repo = BackupJobRepository(conn)
            # Find jobs for device
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM backup_jobs WHERE device_id = ?;", (serial,))
            jobs = cursor.fetchall()
            self.assertEqual(len(jobs), 0)

    def test_acceptance_tablet_readiness_redistribution(self):
        """
        Verify tablet weight redistribution:
        - Base backups: has_contacts=True, has_sms=False, has_call_logs=False.
        - Tablet model (contains "tablet" in name) gets full 45 points if contacts exist (no SMS/calls required).
        """
        serial = "acceptance-tablet-123"
        model = "Acceptance Test Tablet"
        sdk = "31"  # Android 12 (API 31)
        # tablet status
        adb_client = MockAcceptanceAdb(serial=serial, model=model, sdk=sdk, status="device")

        integrator = Sprint2SystemIntegrator(
            db_manager=self.db_manager,
            adb_client=adb_client,
            classifier=self.classifier,
            findings_engine=self.findings_engine,
            recommendation_engine=self.recommendation_engine,
            html_exporter=self.html_exporter,
            pdf_exporter=self.pdf_exporter,
            output_dir=self.temp_dir
        )

        # No sync files created, so it defaults to simulated 80% sync
        # Storage total = 15360000, Synced = 12288000 (0.80) -> Storage Score = 44 points
        # Base: tablet gets 45 points because has_contacts is True.
        # Penalties:
        # - com.google.android.apps.authenticator2: Risk score 100 (CRITICAL) -> penalty 20 points
        # - com.someapp.bank: Risk score 100 (CRITICAL) -> penalty 20 points
        # - com.someapp.utility: Risk score 45 -> severity LOW -> penalty 0 points
        # Total Penalties = 40 points
        # Total score: (45 + 44) - 40 = 49 points.
        result = integrator.execute_system_audit(serial=serial)

        self.assertIsNotNone(result)
        self.assertEqual(result["readiness_score"], 49)


if __name__ == "__main__":
    unittest.main()
