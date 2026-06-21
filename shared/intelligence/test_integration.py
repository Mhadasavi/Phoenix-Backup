"""
Integration tests for the SQLite Database Persistence and Recovery Intelligence Engine
"""

import json
import os
import sqlite3
import tempfile
import unittest
from shared.db.connection import DatabaseConnectionManager
from shared.db.migrations import MigrationRunner
from shared.db.repositories import DeviceRepository, AppInventoryRepository, StorageManifestRepository
from shared.intelligence.rules import RiskKnowledgeBaseLoader
from shared.intelligence.engine import RecoveryIntelligenceEngine

class TestIntelligenceIntegration(unittest.TestCase):

    def setUp(self):
        # Database setup using absolute temp file paths
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_manager = DatabaseConnectionManager(self.temp_db.name)

        # Apply schema migrations (Versions 1 through 5)
        with self.db_manager.get_connection() as conn:
            runner = MigrationRunner(conn)
            runner.run_migrations()

        # Rules configuration setup
        self.temp_rules = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json", encoding="utf-8")
        self.rules_data = [
            {
                "package_pattern": "com.google.android.apps.authenticator2",
                "app_name": "Google Authenticator",
                "category": "AUTHENTICATOR",
                "severity": "CRITICAL",
                "reasoning": "Hardware-backed keys enclave.",
                "remediation": "Export account QR code."
            },
            {
                "package_pattern": "org.thoughtcrime.securesms",
                "app_name": "Signal",
                "category": "SECURE_MESSENGER",
                "severity": "CRITICAL",
                "reasoning": "SQLCipher local DB settings.",
                "remediation": "Enable Signal chat backups."
            }
        ]
        json.dump(self.rules_data, self.temp_rules)
        self.temp_rules.close()

        self.rules_loader = RiskKnowledgeBaseLoader(self.temp_rules.name)

    def tearDown(self):
        os.unlink(self.temp_db.name)
        os.unlink(self.temp_rules.name)

    def test_database_and_engine_integration_pipeline(self):
        device_id = "pixel-7-serial-abc"
        job_id = "job-uuid-123"

        # 1. Seed device, applications, and storage verification manifests
        with self.db_manager.get_connection() as conn:
            device_repo = DeviceRepository(conn)
            app_repo = AppInventoryRepository(conn)
            storage_repo = StorageManifestRepository(conn)

            # Save device details
            device_repo.save_device(
                device_id=device_id,
                manufacturer="Google",
                model="Pixel 7 Pro",
                android_version="14",
                api_level=34
            )

            # Save Google Authenticator (Critical)
            app_repo.save_app(
                device_id=device_id,
                package_name="com.google.android.apps.authenticator2",
                app_name="Google Authenticator",
                version_name="6.0",
                version_code=6000,
                apk_path="/data/app/com.google.android.apps.authenticator2/base.apk",
                is_system=False,
                allow_backup=False,
                backup_source="RULE_MATCH"
            )

            # Save Signal (Critical)
            app_repo.save_app(
                device_id=device_id,
                package_name="org.thoughtcrime.securesms",
                app_name="Signal",
                version_name="6.40.4",
                version_code=6404,
                apk_path="/data/app/org.thoughtcrime.securesms/base.apk",
                is_system=False,
                allow_backup=False,
                backup_source="RULE_MATCH"
            )

            # Save standard social app (No matching rules -> Low risk)
            app_repo.save_app(
                device_id=device_id,
                package_name="com.example.social",
                app_name="Example Social",
                version_name="1.0",
                version_code=100,
                apk_path="/data/app/com.example.social/base.apk",
                is_system=False,
                allow_backup=True,
                backup_source="HEURISTIC_API"
            )

            # Save storage sync: 10GB total, only 5GB synced (50% ratio)
            storage_repo.save_directory_manifest(
                device_id=device_id,
                directory_path="/sdcard/DCIM",
                total_bytes=10000000000,
                synced_bytes=5000000000
            )

        # 2. Run the Recovery Intelligence Engine on the persisted device records
        engine = RecoveryIntelligenceEngine(
            db_manager=self.db_manager,
            rules_loader=self.rules_loader
        )

        # First Audit: Outstanding critical warnings, 50% storage sync
        assessment = engine.evaluate_device_readiness(device_id=device_id, job_id=job_id)
        self.assertIsNotNone(assessment)

        # Score math: 
        # Base core: 15 (contacts) + 15 (SMS) + 15 (call logs) = 45
        # Storage ratio: 50% * 55 = 27
        # Total base: 45 + 27 = 72
        # Penalties: Google Authenticator (Critical = -20), Signal (Critical = -20) -> -40
        # Final Score: 72 - 40 = 32
        self.assertEqual(assessment.readiness_score, 32)
        self.assertEqual(assessment.readiness_state, "CRITICAL_UNPREPARED")
        self.assertEqual(len(assessment.findings), 2)
        self.assertEqual(len(assessment.checklist), 2)
        self.assertEqual(assessment.verdicts["contacts_ready"], True)

        # Check export capabilities
        json_output = engine.export_assessment_to_json(assessment)
        report_data = json.loads(json_output)
        self.assertEqual(report_data["readiness_score"], 32)
        self.assertEqual(report_data["readiness_state"], "CRITICAL_UNPREPARED")

        # Second Audit: User overrides. User resolves the Signal backup checklist warning
        assessment_overridden = engine.evaluate_device_readiness(
            device_id=device_id,
            job_id=job_id,
            user_overrides=["org.thoughtcrime.securesms"]
        )
        self.assertIsNotNone(assessment_overridden)
        
        # Score math:
        # Base core = 45, Storage = 27 -> Total base = 72
        # Penalties: Google Authenticator unresolved = -20 (Signal is resolved)
        # Final Score: 72 - 20 = 52
        self.assertEqual(assessment_overridden.readiness_score, 52)
        self.assertEqual(assessment_overridden.findings[1].resolved, True)  # Signal resolved
        self.assertEqual(assessment_overridden.findings[0].resolved, False) # Authenticator unresolved

if __name__ == "__main__":
    unittest.main()
