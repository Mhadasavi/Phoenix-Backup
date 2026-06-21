"""
Unit tests for the Historical Backup Comparison Engine
"""

import unittest
import os
import sqlite3
from shared.db.connection import DatabaseConnectionManager
from shared.db.migrations import MigrationRunner
from shared.db.repositories import DeviceRepository, BackupJobRepository, JobAppInventoryRepository
from shared.intelligence.comparison import BackupComparisonEngine


class TestBackupComparisonEngine(unittest.TestCase):

    def setUp(self):
        # Set up an in-memory SQLite database and run migrations
        self.db_file = "test_comparison.db"
        if os.path.exists(self.db_file):
            try:
                os.remove(self.db_file)
            except OSError:
                pass
                
        self.db_manager = DatabaseConnectionManager(self.db_file)
        with self.db_manager.get_connection() as conn:
            runner = MigrationRunner(conn)
            runner.run_migrations()

        self.engine = BackupComparisonEngine(self.db_manager)

    def tearDown(self):
        if os.path.exists(self.db_file):
            try:
                os.remove(self.db_file)
            except OSError:
                pass

    def test_compare_different_devices_raises_value_error(self):
        device_a = "device_a_123"
        device_b = "device_b_456"
        job_a = "job_a_1"
        job_b = "job_b_2"

        with self.db_manager.get_connection() as conn:
            dev_repo = DeviceRepository(conn)
            job_repo = BackupJobRepository(conn)

            dev_repo.save_device(device_a, "Google", "Pixel 7", "13", 33)
            dev_repo.save_device(device_b, "Google", "Pixel 8", "14", 34)

            job_repo.create_job(job_a, device_a, "salt", 1000)
            job_repo.create_job(job_b, device_b, "salt", 1000)

        with self.assertRaises(ValueError) as ctx:
            self.engine.compare_jobs(job_a, job_b)
        self.assertIn("different devices", str(ctx.exception))

    def test_compare_missing_jobs_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            self.engine.compare_jobs("non_existent_1", "non_existent_2")
        self.assertIn("not found in database", str(ctx.exception))

    def test_compare_jobs_differential_calculations(self):
        device_id = "device_comparison_test"
        base_job_id = "job_base_100"
        target_job_id = "job_target_200"

        # Initialize base and target database records
        with self.db_manager.get_connection() as conn:
            dev_repo = DeviceRepository(conn)
            job_repo = BackupJobRepository(conn)
            job_app_repo = JobAppInventoryRepository(conn)

            dev_repo.save_device(device_id, "Samsung", "Galaxy S23", "13", 33)

            # Create base job and score = 60
            job_repo.create_job(base_job_id, device_id, "salt", 1000)
            job_repo.update_job_status(base_job_id, "COMPLETED", 60)

            # Create target job and score = 85
            job_repo.create_job(target_job_id, device_id, "salt", 1000)
            job_repo.update_job_status(target_job_id, "COMPLETED", 85)

            # Save base apps inventory:
            # - com.google.android.apps.authenticator2 (AUTHENTICATOR, risk 90, resolved 0)
            # - com.whatsapp (SECURE_MESSENGER, risk 90, resolved 0)
            # - com.example.social (SOCIAL_MEDIA, risk 50, resolved 0)
            base_apps = [
                {
                    "package_name": "com.google.android.apps.authenticator2",
                    "app_name": "Google Authenticator",
                    "category": "AUTHENTICATOR",
                    "risk_score": 90,
                    "resolved": 0
                },
                {
                    "package_name": "com.whatsapp",
                    "app_name": "WhatsApp",
                    "category": "SECURE_MESSENGER",
                    "risk_score": 90,
                    "resolved": 0
                },
                {
                    "package_name": "com.example.social",
                    "app_name": "Social App",
                    "category": "SOCIAL_MEDIA",
                    "risk_score": 50,
                    "resolved": 0
                }
            ]
            job_app_repo.save_job_apps(base_job_id, base_apps)

            # Save target apps inventory:
            # - com.google.android.apps.authenticator2 (AUTHENTICATOR, risk 90, resolved 1) -> RESOLVED finding!
            # - com.whatsapp (removed!)
            # - com.example.social (SOCIAL_MEDIA, risk 50, resolved 0) -> Same
            # - com.chase.sig.android (BANKING, risk 85, resolved 0) -> NEW app!
            target_apps = [
                {
                    "package_name": "com.google.android.apps.authenticator2",
                    "app_name": "Google Authenticator",
                    "category": "AUTHENTICATOR",
                    "risk_score": 90,
                    "resolved": 1
                },
                {
                    "package_name": "com.example.social",
                    "app_name": "Social App",
                    "category": "SOCIAL_MEDIA",
                    "risk_score": 50,
                    "resolved": 0
                },
                {
                    "package_name": "com.chase.sig.android",
                    "app_name": "Chase Mobile",
                    "category": "BANKING",
                    "risk_score": 85,
                    "resolved": 0
                }
            ]
            job_app_repo.save_job_apps(target_job_id, target_apps)

        # Execute Comparison
        report = self.engine.compare_jobs(base_job_id, target_job_id)

        # Assertions
        self.assertEqual(report.base_job_id, base_job_id)
        self.assertEqual(report.target_job_id, target_job_id)
        self.assertEqual(report.base_readiness_score, 60)
        self.assertEqual(report.target_readiness_score, 85)
        self.assertEqual(report.readiness_score_delta, 25)
        self.assertEqual(report.readiness_improved, True)
        self.assertEqual(report.inventory_size_delta, 0)

        # Added apps check
        self.assertEqual(len(report.added_apps), 1)
        self.assertEqual(report.added_apps[0]["package_name"], "com.chase.sig.android")
        self.assertEqual(report.added_apps[0]["category"], "BANKING")

        # Removed apps check
        self.assertEqual(len(report.removed_apps), 1)
        self.assertEqual(report.removed_apps[0]["package_name"], "com.whatsapp")

        # New Risks check:
        # Chase Mobile is added and has risk 85 (>= 50), so it is a new risk!
        self.assertEqual(len(report.new_risks), 1)
        self.assertEqual(report.new_risks[0]["package_name"], "com.chase.sig.android")
        self.assertIn("New application installed", report.new_risks[0]["reason"])

        # Resolved Risks check:
        # 1. Google Authenticator finding became resolved.
        # 2. WhatsApp (risk 90) was removed.
        self.assertEqual(len(report.resolved_risks), 2)
        resolved_packages = [r["package_name"] for r in report.resolved_risks]
        self.assertIn("com.google.android.apps.authenticator2", resolved_packages)
        self.assertIn("com.whatsapp", resolved_packages)
        
        auth_resolved = next(r for r in report.resolved_risks if r["package_name"] == "com.google.android.apps.authenticator2")
        self.assertIn("override applied", auth_resolved["reason"])
        
        wa_resolved = next(r for r in report.resolved_risks if r["package_name"] == "com.whatsapp")
        self.assertIn("uninstalled", wa_resolved["reason"])


if __name__ == "__main__":
    unittest.main()
