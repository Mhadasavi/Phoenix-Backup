"""
Unit tests for the SQLite Database Persistence module
"""

import os
import unittest
import sqlite3
from .connection import DatabaseConnectionManager
from .migrations import MigrationRunner
from .repositories import DeviceRepository, BackupJobRepository, AuditLogRepository


class TestDatabasePersistence(unittest.TestCase):

    def setUp(self):
        """
        Creates an in-memory database configuration and applies baseline schemas.
        """
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        
        # Initialize and apply migrations
        self.runner = MigrationRunner(self.conn)
        self.runner.run_migrations()

    def tearDown(self):
        self.conn.close()

    def test_database_connection_manager_resolves_absolute_paths(self):
        """
        Verify relative database path input is converted to absolute filesystem paths.
        """
        # Test file target
        manager = DatabaseConnectionManager("local_relative_path.db")
        self.assertTrue(os.path.isabs(manager.db_path))

        # Test memory target (keeps raw string)
        mem_manager = DatabaseConnectionManager(":memory:")
        self.assertEqual(mem_manager.db_path, ":memory:")

    def test_database_connection_manager_context_works_on_memory(self):
        """
        Verify context manager executes successfully on :memory: targets without WAL errors.
        """
        manager = DatabaseConnectionManager(":memory:")
        with manager.get_connection() as conn:
            runner = MigrationRunner(conn)
            applied = runner.run_migrations()
            self.assertEqual(applied, 8) # 3 tables + 2 indexes + 2 Sprint 2 tables + 1 Version 6 table

    def test_migrations_create_expected_tables(self):
        """
        Verify that schema tables exist after migration.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        self.assertIn("devices", tables)
        self.assertIn("backup_jobs", tables)
        self.assertIn("audit_logs", tables)
        self.assertIn("schema_migrations", tables)
        self.assertIn("job_app_inventory", tables)

    def test_device_repository_insert_and_upsert(self):
        """
        Verify device save and conflict updating (upsert).
        """
        repo = DeviceRepository(self.conn)
        
        # Save device
        repo.save_device("serial-123", "Samsung", "S21", "12", 31)
        device = repo.get_device("serial-123")
        
        self.assertIsNotNone(device)
        self.assertEqual(device["manufacturer"], "Samsung")
        self.assertEqual(device["model"], "S21")
        self.assertEqual(device["android_version"], "12")
        self.assertEqual(device["api_level"], 31)
        
        # Upsert: Update android version and API level
        repo.save_device("serial-123", "Samsung", "S21", "13", 33)
        updated = repo.get_device("serial-123")
        
        self.assertEqual(updated["android_version"], "13")
        self.assertEqual(updated["api_level"], 33)

    def test_backup_job_repository_creation_and_status(self):
        """
        Verify job creation, status updates, and duration log updates.
        """
        device_repo = DeviceRepository(self.conn)
        job_repo = BackupJobRepository(self.conn)
        
        # Create parent device (needed due to foreign key constraints)
        device_repo.save_device("serial-123", "Pixel", "5", "11", 30)

        # Create backup job
        job_repo.create_job("job-abc", "serial-123", "salt_hex_val", 100000)
        job = job_repo.get_job("job-abc")
        
        self.assertIsNotNone(job)
        self.assertEqual(job["status"], "STARTED")
        self.assertEqual(job["encryption_salt"], "salt_hex_val")
        self.assertIsNone(job["end_time"])

        # Update status
        job_repo.update_job_status("job-abc", "COMPLETED", score=85)
        completed_job = job_repo.get_job("job-abc")
        
        self.assertEqual(completed_job["status"], "COMPLETED")
        self.assertEqual(completed_job["readiness_score"], 85)
        self.assertIsNotNone(completed_job["end_time"])

    def test_foreign_key_constraint_enforcement(self):
        """
        Verify SQLite raises IntegrityError if inserting job on non-existent device.
        """
        job_repo = BackupJobRepository(self.conn)
        
        # Try to insert a job pointing to missing device ID (serial-999)
        with self.assertRaises(sqlite3.IntegrityError):
            job_repo.create_job("job-fail", "serial-999", "salt_val", 100)

    def test_audit_logs_repository(self):
        """
        Verify audit logging insertion and paging queries.
        """
        repo = AuditLogRepository(self.conn)
        
        repo.log("INFO", "BACKUP_ENGINE", "Starting file crawls...")
        repo.log("ERROR", "CRYPTO", "Invalid password layout")
        
        logs = repo.get_recent_logs(limit=10)
        self.assertEqual(len(logs), 2)
        
        # Order is descending by timestamp
        self.assertEqual(logs[0]["log_level"], "ERROR")
        self.assertEqual(logs[0]["module"], "CRYPTO")
        
        self.assertEqual(logs[1]["log_level"], "INFO")
        self.assertEqual(logs[1]["module"], "BACKUP_ENGINE")


if __name__ == "__main__":
    unittest.main()
