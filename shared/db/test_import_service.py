import unittest
import sqlite3
import json
from shared.db.import_service import BackupImportService

class TestBackupImportService(unittest.TestCase):

    def setUp(self):
        # Create in-memory database context
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        
        # Setup mock parent tables
        self.conn.execute("""
            CREATE TABLE devices (
                device_id TEXT PRIMARY KEY,
                manufacturer TEXT NOT NULL,
                model TEXT NOT NULL,
                android_version TEXT NOT NULL,
                api_level INTEGER NOT NULL
            );
        """)
        self.conn.execute("""
            CREATE TABLE backup_jobs (
                job_id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                status TEXT NOT NULL,
                encryption_salt TEXT,
                key_derivation_rounds INTEGER,
                FOREIGN KEY(device_id) REFERENCES devices(device_id)
            );
        """)
        self.conn.commit()

        # Seed mock device and backup job
        self.conn.execute("INSERT INTO devices VALUES ('dev123', 'Google', 'Pixel', '13', 33);")
        self.conn.execute("INSERT INTO backup_jobs VALUES ('job123', 'dev123', 'STARTED', 'salt', 1000);")
        self.conn.commit()

        self.service = BackupImportService(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_contacts_import_success(self):
        contacts_payload = {
            "status": "SUCCESS",
            "data": {
                "contacts": [
                    {
                        "name": "Jane Doe",
                        "phones": ["+15550100", "+15550111"],
                        "emails": ["jane@example.com"]
                    },
                    {
                        "name": "John Smith",
                        "phones": [],
                        "emails": []
                    }
                ]
            }
        }
        
        payload_str = json.dumps(contacts_payload)
        result = self.service.import_contacts("job123", payload_str)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["records_imported"], 2)

        # Assert database content
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM job_contacts ORDER BY name ASC;")
        rows = cursor.fetchall()
        
        self.assertEqual(len(rows), 2)
        
        self.assertEqual(rows[0]["name"], "Jane Doe")
        self.assertEqual(rows[0]["phones"], "+15550100,+15550111")
        self.assertEqual(rows[0]["emails"], "jane@example.com")
        
        self.assertEqual(rows[1]["name"], "John Smith")
        self.assertEqual(rows[1]["phones"], "")
        self.assertEqual(rows[1]["emails"], "")

        # Verify extraction log record
        cursor.execute("SELECT * FROM job_extraction_logs WHERE data_type = 'CONTACTS';")
        log = cursor.fetchone()
        self.assertIsNotNone(log)
        self.assertEqual(log["status"], "SUCCESS")
        self.assertEqual(log["records_extracted"], 2)

    def test_contacts_import_permission_denied(self):
        denied_payload = {
            "status": "PERMISSION_DENIED",
            "message": "User rejected contacts query permission request"
        }
        
        result = self.service.import_contacts("job123", json.dumps(denied_payload))
        
        self.assertFalse(result["success"])
        self.assertIn("permission denied", result["error"].lower())

        # Assert no database records were inserted
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM job_contacts;")
        self.assertEqual(cursor.fetchone()[0], 0)

        # Verify extraction log reports failed status
        cursor.execute("SELECT * FROM job_extraction_logs WHERE data_type = 'CONTACTS';")
        log = cursor.fetchone()
        self.assertIsNotNone(log)
        self.assertEqual(log["status"], "FAILED")

    def test_sms_import_success(self):
        sms_payload = {
            "status": "SUCCESS",
            "data": {
                "sms": [
                    {
                        "address": "+15550100",
                        "body": "Hello World",
                        "timestamp": 1781446700000,
                        "type": "INBOX"
                    },
                    {
                        "address": "+15550111",
                        "body": "Test msg",
                        "timestamp": 1781446705000,
                        "type": "SENT"
                    }
                ]
            }
        }
        
        result = self.service.import_sms("job123", json.dumps(sms_payload))
        
        self.assertTrue(result["success"])
        self.assertEqual(result["records_imported"], 2)

        # Assert database content
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM job_sms ORDER BY timestamp ASC;")
        rows = cursor.fetchall()
        
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["address"], "+15550100")
        self.assertEqual(rows[0]["body"], "Hello World")
        self.assertEqual(rows[0]["type"], "INBOX")

        # Verify extraction log record
        cursor.execute("SELECT * FROM job_extraction_logs WHERE data_type = 'SMS';")
        log = cursor.fetchone()
        self.assertIsNotNone(log)
        self.assertEqual(log["status"], "SUCCESS")
        self.assertEqual(log["records_extracted"], 2)

    def test_call_logs_import_success(self):
        call_payload = {
            "status": "SUCCESS",
            "data": {
                "call_logs": [
                    {
                        "number": "+15550100",
                        "timestamp": 1781446700000,
                        "duration": 45,
                        "type": "INCOMING",
                        "name": "Jane Doe"
                    }
                ]
            }
        }
        
        result = self.service.import_call_logs("job123", json.dumps(call_payload))
        
        self.assertTrue(result["success"])
        self.assertEqual(result["records_imported"], 1)

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM job_call_logs;")
        rows = cursor.fetchall()
        
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["number"], "+15550100")
        self.assertEqual(rows[0]["duration"], 45)
        self.assertEqual(rows[0]["type"], "INCOMING")
        self.assertEqual(rows[0]["name"], "Jane Doe")

        # Verify extraction log record
        cursor.execute("SELECT * FROM job_extraction_logs WHERE data_type = 'CALL_LOGS';")
        log = cursor.fetchone()
        self.assertIsNotNone(log)
        self.assertEqual(log["status"], "SUCCESS")
        self.assertEqual(log["records_extracted"], 1)

    def test_transactional_rollback_on_failed_row(self):
        # Payload where second item is missing 'address' (required column)
        bad_sms_payload = {
            "status": "SUCCESS",
            "data": {
                "sms": [
                    {
                        "address": "+15550100",
                        "body": "Good msg",
                        "timestamp": 1781446700000,
                        "type": "INBOX"
                    },
                    {
                        "body": "Bad msg missing address",
                        "timestamp": 1781446705000,
                        "type": "SENT"
                    }
                ]
            }
        }
        
        result = self.service.import_sms("job123", json.dumps(bad_sms_payload))
        
        self.assertFalse(result["success"])
        self.assertIn("missing required field", result["error"])

        # Check database: first row must be rolled back
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM job_sms;")
        self.assertEqual(cursor.fetchone()[0], 0)

        # Check extraction logs: must log FAILED status
        cursor.execute("SELECT * FROM job_extraction_logs WHERE data_type = 'SMS';")
        log = cursor.fetchone()
        self.assertEqual(log["status"], "FAILED")
        self.assertEqual(log["records_extracted"], 0)

if __name__ == "__main__":
    unittest.main()
