"""
Phoenix Backup Host-Side Data Import Service
"""

import json
import logging
import sqlite3
from typing import Dict, Any, List

logger = logging.getLogger("phoenix.db.import_service")

class BackupImportService:
    """
    Handles JSON validation and transactional persistence of Contacts, SMS,
    and Call Logs into the host SQLite database.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._initialize_tables()

    def _initialize_tables(self) -> None:
        """
        Ensure all target backup data tables and extraction trackers exist.
        """
        ddl_statements = [
            """
            CREATE TABLE IF NOT EXISTS job_contacts (
                job_id TEXT NOT NULL,
                name TEXT NOT NULL,
                phones TEXT, -- comma-separated string of phone numbers
                emails TEXT, -- comma-separated string of emails
                PRIMARY KEY(job_id, name),
                FOREIGN KEY(job_id) REFERENCES backup_jobs(job_id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS job_sms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                address TEXT NOT NULL,
                body TEXT,
                timestamp INTEGER NOT NULL,
                type TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES backup_jobs(job_id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS job_call_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                number TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                duration INTEGER NOT NULL,
                type TEXT NOT NULL,
                name TEXT,
                FOREIGN KEY(job_id) REFERENCES backup_jobs(job_id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS job_extraction_logs (
                job_id TEXT NOT NULL,
                data_type TEXT NOT NULL CHECK(data_type IN ('CONTACTS', 'SMS', 'CALL_LOGS', 'SYSTEM_INFO')),
                status TEXT NOT NULL CHECK(status IN ('SUCCESS', 'FAILED', 'PERMISSION_DENIED')),
                records_extracted INTEGER NOT NULL DEFAULT 0,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(job_id, data_type),
                FOREIGN KEY(job_id) REFERENCES backup_jobs(job_id) ON DELETE CASCADE
            );
            """
        ]
        
        try:
            for ddl in ddl_statements:
                self.conn.execute(ddl)
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error("Failed to initialize import service database tables: %s", e)
            self.conn.rollback()
            raise e

    def import_contacts(self, job_id: str, payload_str: str) -> Dict[str, Any]:
        """
        Parses and imports Contacts JSON payload into job_contacts.
        """
        try:
            payload = json.loads(payload_str)
            self._validate_payload_envelope(payload)
            
            data = payload.get("data", {})
            contacts = data.get("contacts", [])
            
            # Write to DB
            sql = """
                INSERT OR REPLACE INTO job_contacts (job_id, name, phones, emails)
                VALUES (?, ?, ?, ?);
            """
            
            for contact in contacts:
                name = contact.get("name")
                if not name:
                    raise ValueError("Contact record missing required field 'name'")
                
                # Convert list values to clean strings
                phones = ",".join(contact.get("phones", []))
                emails = ",".join(contact.get("emails", []))
                
                self.conn.execute(sql, (job_id, name, phones, emails))
            
            self._log_extraction(job_id, "CONTACTS", "SUCCESS", len(contacts))
            self.conn.commit()
            
            return {"success": True, "records_imported": len(contacts)}
            
        except Exception as e:
            logger.error("Contacts import failed for job %s: %s", job_id, e)
            self.conn.rollback()
            self._log_extraction(job_id, "CONTACTS", "FAILED", 0)
            return {"success": False, "error": str(e)}

    def import_sms(self, job_id: str, payload_str: str) -> Dict[str, Any]:
        """
        Parses and imports SMS JSON payload into job_sms.
        """
        try:
            payload = json.loads(payload_str)
            self._validate_payload_envelope(payload)
            
            data = payload.get("data", {})
            sms_list = data.get("sms", [])
            
            sql = """
                INSERT INTO job_sms (job_id, address, body, timestamp, type)
                VALUES (?, ?, ?, ?, ?);
            """
            
            for sms in sms_list:
                address = sms.get("address")
                timestamp = sms.get("timestamp")
                sms_type = sms.get("type")
                
                if address is None or timestamp is None or not sms_type:
                    raise ValueError("SMS record missing required field 'address', 'timestamp', or 'type'")
                
                self.conn.execute(sql, (job_id, address, sms.get("body", ""), timestamp, sms_type))
            
            self._log_extraction(job_id, "SMS", "SUCCESS", len(sms_list))
            self.conn.commit()
            
            return {"success": True, "records_imported": len(sms_list)}
            
        except Exception as e:
            logger.error("SMS import failed for job %s: %s", job_id, e)
            self.conn.rollback()
            self._log_extraction(job_id, "SMS", "FAILED", 0)
            return {"success": False, "error": str(e)}

    def import_call_logs(self, job_id: str, payload_str: str) -> Dict[str, Any]:
        """
        Parses and imports Call Log JSON payload into job_call_logs.
        """
        try:
            payload = json.loads(payload_str)
            self._validate_payload_envelope(payload)
            
            data = payload.get("data", {})
            call_logs = data.get("call_logs", [])
            
            sql = """
                INSERT INTO job_call_logs (job_id, number, timestamp, duration, type, name)
                VALUES (?, ?, ?, ?, ?, ?);
            """
            
            for log in call_logs:
                number = log.get("number")
                timestamp = log.get("timestamp")
                duration = log.get("duration")
                log_type = log.get("type")
                
                if number is None or timestamp is None or duration is None or not log_type:
                    raise ValueError("Call Log record missing required field 'number', 'timestamp', 'duration', or 'type'")
                
                self.conn.execute(sql, (job_id, number, timestamp, duration, log_type, log.get("name", "")))
            
            self._log_extraction(job_id, "CALL_LOGS", "SUCCESS", len(call_logs))
            self.conn.commit()
            
            return {"success": True, "records_imported": len(call_logs)}
            
        except Exception as e:
            logger.error("Call logs import failed for job %s: %s", job_id, e)
            self.conn.rollback()
            self._log_extraction(job_id, "CALL_LOGS", "FAILED", 0)
            return {"success": False, "error": str(e)}

    def _validate_payload_envelope(self, payload: Dict[str, Any]) -> None:
        """
        Assures JSON packets match core companion API envelope responses.
        """
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a JSON object")
        
        status = payload.get("status")
        if status == "PERMISSION_DENIED":
            raise PermissionError("Mobile agent reports permission denied for this data type")
        
        if status != "SUCCESS":
            message = payload.get("message", "No details provided")
            raise ValueError(f"Invalid payload envelope status: '{status}'. Message: {message}")
        
        if "data" not in payload:
            raise ValueError("Payload missing required 'data' field envelope")

    def _log_extraction(self, job_id: str, data_type: str, status: str, count: int) -> None:
        """
        Records extraction results to the database tracker.
        """
        sql = """
            INSERT OR REPLACE INTO job_extraction_logs (job_id, data_type, status, records_extracted)
            VALUES (?, ?, ?, ?);
        """
        try:
            self.conn.execute(sql, (job_id, data_type, status, count))
        except sqlite3.Error as e:
            logger.error("Failed to write extraction log for job %s (%s): %s", job_id, data_type, e)
            # Do not raise here to prevent rolling back successful database updates
