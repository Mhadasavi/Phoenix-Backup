import unittest
from unittest.mock import Mock, patch
import sqlite3
from shared.orchestrator.backup_runner import BackupRunner
from shared.db.migrations import MigrationRunner
from shared.db.import_service import BackupImportService

class TestBackupRunner(unittest.TestCase):

    def setUp(self):
        # Create an in-memory SQLite database
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        
        # Apply standard schema migrations
        migrator = MigrationRunner(self.conn)
        migrator.run_migrations()
        
        # Initialize import service to bootstrap contacts and extraction log tables
        self.importer = BackupImportService(self.conn)
        
        self.runner = BackupRunner(self.conn, token="test_token")

    def tearDown(self):
        self.conn.close()

    @patch("shared.orchestrator.backup_runner.SecureTransportClient")
    def test_execute_backup_success(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.session_id = "test-session-id"

        # Mock calls sequentially: System Info -> Contacts Batch (1 page) -> SMS Batch (1 page) -> Call Logs Batch (1 page)
        mock_client.send_command.side_effect = [
            # 1. GET_SYSTEM_INFO
            {
                "status": "SUCCESS",
                "data": {
                    "manufacturer": "Google",
                    "model": "Pixel 7",
                    "android_version": "14",
                    "api_level": 34
                }
            },
            # 2. GET_CONTACTS
            {
                "status": "SUCCESS",
                "data": {
                    "contacts": [
                        {
                            "name": "Jane Doe",
                            "phones": ["+15550199"],
                            "emails": ["jane.doe@example.com"]
                        }
                    ],
                    "has_more": False
                }
            },
            # 3. GET_SMS
            {
                "status": "SUCCESS",
                "data": {
                    "sms": [
                        {
                            "id": "1",
                            "address": "+15550199",
                            "body": "Hello",
                            "timestamp": 1620000000000,
                            "type": "INBOX"
                        }
                    ],
                    "has_more": False
                }
            },
            # 4. GET_CALL_LOGS
            {
                "status": "SUCCESS",
                "data": {
                    "call_logs": [
                        {
                            "id": "1",
                            "number": "+15550199",
                            "timestamp": 1620000000000,
                            "duration": 60,
                            "type": "INCOMING",
                            "name": "Jane Doe"
                        }
                    ],
                    "has_more": False
                }
            }
        ]

        job_id = self.runner.execute_backup(serial="device123")
        self.assertIsNotNone(job_id)

        # Assert database updates
        cursor = self.conn.cursor()
        
        # Verify job status
        cursor.execute("SELECT status, readiness_score FROM backup_jobs WHERE job_id = ?;", (job_id,))
        job = cursor.fetchone()
        self.assertIsNotNone(job)
        self.assertEqual(job["status"], "COMPLETED")

        # Verify device record
        cursor.execute("SELECT manufacturer, model FROM devices WHERE device_id = ?;", ("device123",))
        device = cursor.fetchone()
        self.assertIsNotNone(device)
        self.assertEqual(device["manufacturer"], "Google")
        self.assertEqual(device["model"], "Pixel 7")

        # Verify contact imported
        cursor.execute("SELECT name, phones, emails FROM job_contacts WHERE job_id = ?;", (job_id,))
        contact = cursor.fetchone()
        self.assertIsNotNone(contact)
        self.assertEqual(contact["name"], "Jane Doe")
        self.assertEqual(contact["phones"], "+15550199")
        self.assertEqual(contact["emails"], "jane.doe@example.com")

        # Verify SMS imported
        cursor.execute("SELECT address, body, timestamp, type FROM job_sms WHERE job_id = ?;", (job_id,))
        sms = cursor.fetchone()
        self.assertIsNotNone(sms)
        self.assertEqual(sms["address"], "+15550199")
        self.assertEqual(sms["body"], "Hello")
        self.assertEqual(sms["timestamp"], 1620000000000)
        self.assertEqual(sms["type"], "INBOX")

        # Verify Call Log imported
        cursor.execute("SELECT number, timestamp, duration, type, name FROM job_call_logs WHERE job_id = ?;", (job_id,))
        call_log = cursor.fetchone()
        self.assertIsNotNone(call_log)
        self.assertEqual(call_log["number"], "+15550199")
        self.assertEqual(call_log["timestamp"], 1620000000000)
        self.assertEqual(call_log["duration"], 60)
        self.assertEqual(call_log["type"], "INCOMING")
        self.assertEqual(call_log["name"], "Jane Doe")

        # Verify extraction logs are recorded
        cursor.execute("SELECT data_type, status, records_extracted FROM job_extraction_logs WHERE job_id = ? ORDER BY data_type;", (job_id,))
        logs = cursor.fetchall()
        self.assertEqual(len(logs), 3)
        self.assertEqual(logs[0]["data_type"], "CALL_LOGS")
        self.assertEqual(logs[0]["status"], "SUCCESS")
        self.assertEqual(logs[0]["records_extracted"], 1)
        self.assertEqual(logs[1]["data_type"], "CONTACTS")
        self.assertEqual(logs[1]["status"], "SUCCESS")
        self.assertEqual(logs[1]["records_extracted"], 1)
        self.assertEqual(logs[2]["data_type"], "SMS")
        self.assertEqual(logs[2]["status"], "SUCCESS")
        self.assertEqual(logs[2]["records_extracted"], 1)

    @patch("shared.orchestrator.backup_runner.SecureTransportClient")
    def test_execute_backup_failure(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.session_id = "test-session-id"

        # Mock GET_SYSTEM_INFO failure
        mock_client.send_command.return_value = {
            "status": "ERROR",
            "message": "Connection closed unexpectedly"
        }

        job_id = self.runner.execute_backup(serial="device123")
        self.assertIsNone(job_id)

if __name__ == "__main__":
    unittest.main()
