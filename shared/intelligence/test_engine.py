"""
Unit tests for the Recovery Intelligence Engine Orchestrator
"""

import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock
from shared.db.connection import DatabaseConnectionManager
from shared.db.migrations import MigrationRunner
from shared.db.repositories import DeviceRepository, AppInventoryRepository, StorageManifestRepository
from shared.intelligence.rules import RiskKnowledgeBaseLoader
from shared.intelligence.engine import RecoveryIntelligenceEngine

class TestIntelligenceEngine(unittest.TestCase):

    def setUp(self):
        # Database setup
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_manager = DatabaseConnectionManager(self.temp_db.name)
        with self.db_manager.get_connection() as conn:
            runner = MigrationRunner(conn)
            runner.run_migrations()

        # Seed mock device data
        self.device_id = "test-device-123"
        with self.db_manager.get_connection() as conn:
            device_repo = DeviceRepository(conn)
            device_repo.save_device(
                device_id=self.device_id,
                manufacturer="Google",
                model="Pixel 6",
                android_version="13",
                api_level=33
            )

        # Rules config setup
        self.temp_rules = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json", encoding="utf-8")
        self.rules_data = [
            {
                "package_pattern": "com.google.android.apps.authenticator2",
                "app_name": "Google Authenticator",
                "category": "AUTHENTICATOR",
                "severity": "CRITICAL",
                "reasoning": "TOTP hardware enclaves.",
                "remediation": "Export QR."
            }
        ]
        json.dump(self.rules_data, self.temp_rules)
        self.temp_rules.close()

        self.rules_loader = RiskKnowledgeBaseLoader(self.temp_rules.name)

    def tearDown(self):
        os.unlink(self.temp_db.name)
        os.unlink(self.temp_rules.name)

    def test_evaluate_device_readiness_basic(self):
        # Write app inventory and storage sync details to database
        with self.db_manager.get_connection() as conn:
            app_repo = AppInventoryRepository(conn)
            storage_repo = StorageManifestRepository(conn)

            # Save app
            app_repo.save_app(
                device_id=self.device_id,
                package_name="com.google.android.apps.authenticator2",
                app_name="Google Authenticator",
                version_name="5.10",
                version_code=5100,
                apk_path="/data/app/com.google.android.apps.authenticator2/base.apk",
                is_system=False,
                allow_backup=False,
                backup_source="RULE_MATCH"
            )

            # Save storage sync state
            storage_repo.save_directory_manifest(
                device_id=self.device_id,
                directory_path="/sdcard/DCIM",
                total_bytes=1000,
                synced_bytes=0
            )

        # Initialize engine
        engine = RecoveryIntelligenceEngine(
            db_manager=self.db_manager,
            rules_loader=self.rules_loader
        )

        # Execute evaluation
        assessment = engine.evaluate_device_readiness(
            device_id=self.device_id,
            job_id="test-job-uuid"
        )

        self.assertIsNotNone(assessment)
        self.assertEqual(len(assessment.findings), 1)
        self.assertEqual(assessment.findings[0].package_name, "com.google.android.apps.authenticator2")
        self.assertEqual(assessment.findings[0].severity, "CRITICAL")
        self.assertEqual(assessment.readiness_state, "CRITICAL_UNPREPARED")

        # Verify JSON Export formats
        json_output = engine.export_assessment_to_json(assessment)
        data = json.loads(json_output)
        self.assertEqual(data["readiness_state"], "CRITICAL_UNPREPARED")
        self.assertEqual(len(data["findings"]), 1)
        self.assertEqual(data["findings"][0]["package_name"], "com.google.android.apps.authenticator2")

    def test_evaluate_device_readiness_with_user_overrides(self):
        with self.db_manager.get_connection() as conn:
            app_repo = AppInventoryRepository(conn)
            storage_repo = StorageManifestRepository(conn)

            app_repo.save_app(
                device_id=self.device_id,
                package_name="com.google.android.apps.authenticator2",
                app_name="Google Authenticator",
                version_name="5.10",
                version_code=5100,
                apk_path="/data/app/com.google.android.apps.authenticator2/base.apk",
                is_system=False,
                allow_backup=False,
                backup_source="RULE_MATCH"
            )

            storage_repo.save_directory_manifest(
                device_id=self.device_id,
                directory_path="/sdcard/DCIM",
                total_bytes=1000,
                synced_bytes=1000
            )

        engine = RecoveryIntelligenceEngine(
            db_manager=self.db_manager,
            rules_loader=self.rules_loader
        )

        # Execute evaluation with user overrides acknowledging Google Authenticator is secured
        assessment = engine.evaluate_device_readiness(
            device_id=self.device_id,
            job_id="test-job-uuid",
            user_overrides=["com.google.android.apps.authenticator2"]
        )

        self.assertIsNotNone(assessment)
        self.assertEqual(len(assessment.findings), 1)
        self.assertTrue(assessment.findings[0].resolved)
        # Score is now back to optimal since the penalty is resolved
        self.assertEqual(assessment.readiness_score, 100)
        self.assertEqual(assessment.readiness_state, "READY")

if __name__ == "__main__":
    unittest.main()
