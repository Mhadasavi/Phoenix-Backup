import logging
import sqlite3
import uuid
import json
from typing import Dict, Any, Optional

from shared.network.client import SecureTransportClient
from shared.db.repositories import DeviceRepository, BackupJobRepository, AuditLogRepository
from shared.db.import_service import BackupImportService

logger = logging.getLogger("phoenix.orchestrator.backup_runner")

class BackupRunner:
    """
    Orchestrates the data extraction backup flow:
    Connects to device -> Authenticates -> Fetches System Info -> Registers Job ->
    Extracts data (Contacts) in paginated chunks -> Persists to SQLite.
    """

    def __init__(self, conn: sqlite3.Connection, token: str, host: str = "127.0.0.1", port: int = 50051):
        self.conn = conn
        self.token = token
        self.host = host
        self.port = port
        self.client = None
        self.device_repo = DeviceRepository(conn)
        self.job_repo = BackupJobRepository(conn)
        self.audit_repo = AuditLogRepository(conn)
        self.import_service = BackupImportService(conn)

    def execute_backup(self, serial: str) -> Optional[str]:
        """
        Executes the Contacts Extraction vertical slice.
        Returns the job_id on success, or None on failure.
        """
        job_id = str(uuid.uuid4())
        logger.info("Starting backup run for serial: %s. Job ID: %s", serial, job_id)
        self.audit_repo.log("INFO", "BACKUP_ORCHESTRATOR", f"Starting backup job {job_id} for device {serial}")

        self.client = SecureTransportClient(host=self.host, port=self.port)
        try:
            # 1. Establish Secure Transport Connection
            logger.info("Connecting to Android SecureTransportServer at %s:%d...", self.host, self.port)
            self.client.connect()
            self.client.authenticate(self.token)
            logger.info("Secure handshake completed successfully. Session ID: %s", self.client.session_id)

            # 2. Retrieve System Hardware Information
            logger.info("Fetching hardware configuration...")
            sys_info_resp = self.client.send_command("GET_SYSTEM_INFO")
            if sys_info_resp.get("status") != "SUCCESS":
                raise RuntimeError(f"Failed to fetch system info: {sys_info_resp.get('message')}")

            sys_data = sys_info_resp.get("data", {})
            manufacturer = sys_data.get("manufacturer") or "Unknown"
            model = sys_data.get("model") or "Unknown"
            android_ver = sys_data.get("android_version") or "Unknown"
            api_level = sys_data.get("api_level") or 30

            # 3. Register Device and Create Started Job
            self.device_repo.save_device(
                device_id=serial,
                manufacturer=manufacturer,
                model=model,
                android_version=android_ver,
                api_level=api_level
            )
            self.job_repo.create_job(
                job_id=job_id,
                device_id=serial,
                salt=self.token,  # Use token salt
                rounds=100000
            )
            self.conn.commit()

            # 4. Extract Contacts (Paginated)
            logger.info("Beginning Contacts Extraction vertical slice...")
            self.audit_repo.log("INFO", "BACKUP_ORCHESTRATOR", "Beginning Contacts extraction chunk loops")
            
            limit = 1000
            offset = 0
            has_more = True
            total_contacts = 0

            while has_more:
                logger.info("Requesting Contacts batch. Limit: %d, Offset: %d", limit, offset)
                contacts_resp = self.client.send_command("GET_CONTACTS", {"limit": limit, "offset": offset})
                
                # Import results using database importer
                import_res = self.import_service.import_contacts(job_id, json_payload_string(contacts_resp))
                if not import_res.get("success"):
                    raise RuntimeError(f"Contacts import database write failure: {import_res.get('error')}")

                records_imported = import_res.get("records_imported", 0)
                total_contacts += records_imported
                logger.info("Successfully imported %d contact records", records_imported)

                # Check pagination bounds
                data_envelope = contacts_resp.get("data", {})
                has_more = data_envelope.get("has_more", False)
                
                if records_imported == 0:
                    break

                offset += records_imported

            # 5. Extract SMS (Paginated)
            logger.info("Beginning SMS Extraction...")
            self.audit_repo.log("INFO", "BACKUP_ORCHESTRATOR", "Beginning SMS extraction chunk loops")
            
            offset = 0
            has_more = True
            total_sms = 0

            while has_more:
                logger.info("Requesting SMS batch. Limit: %d, Offset: %d", limit, offset)
                sms_resp = self.client.send_command("GET_SMS", {"limit": limit, "offset": offset})
                
                # Import results using database importer
                import_res = self.import_service.import_sms(job_id, json_payload_string(sms_resp))
                if not import_res.get("success"):
                    raise RuntimeError(f"SMS import database write failure: {import_res.get('error')}")

                records_imported = import_res.get("records_imported", 0)
                total_sms += records_imported
                logger.info("Successfully imported %d SMS records", records_imported)

                # Check pagination bounds
                data_envelope = sms_resp.get("data", {})
                has_more = data_envelope.get("has_more", False)
                
                if records_imported == 0:
                    break

                offset += records_imported

            # 6. Extract Call Logs (Paginated)
            logger.info("Beginning Call Logs Extraction...")
            self.audit_repo.log("INFO", "BACKUP_ORCHESTRATOR", "Beginning Call Logs extraction chunk loops")
            
            offset = 0
            has_more = True
            total_call_logs = 0

            while has_more:
                logger.info("Requesting Call Logs batch. Limit: %d, Offset: %d", limit, offset)
                call_logs_resp = self.client.send_command("GET_CALL_LOGS", {"limit": limit, "offset": offset})
                
                # Import results using database importer
                import_res = self.import_service.import_call_logs(job_id, json_payload_string(call_logs_resp))
                if not import_res.get("success"):
                    raise RuntimeError(f"Call logs import database write failure: {import_res.get('error')}")

                records_imported = import_res.get("records_imported", 0)
                total_call_logs += records_imported
                logger.info("Successfully imported %d Call Log records", records_imported)

                # Check pagination bounds
                data_envelope = call_logs_resp.get("data", {})
                has_more = data_envelope.get("has_more", False)
                
                if records_imported == 0:
                    break

                offset += records_imported

            # 7. Complete Job successfully
            logger.info("Extraction complete. Contacts: %d, SMS: %d, Call Logs: %d.", total_contacts, total_sms, total_call_logs)
            self.job_repo.update_job_status(job_id, "COMPLETED")
            self.audit_repo.log("INFO", "BACKUP_ORCHESTRATOR", f"Backup completed successfully. Saved {total_contacts} contacts, {total_sms} SMS, {total_call_logs} call logs.")
            self.conn.commit()
            return job_id

        except Exception as e:
            logger.error("Fatal error during backup execution: %s", e)
            self.audit_repo.log("ERROR", "BACKUP_ORCHESTRATOR", f"Backup runner crashed: {str(e)}")
            try:
                self.job_repo.update_job_status(job_id, "FAILED")
                self.conn.commit()
            except Exception:
                pass
            return None
        finally:
            if self.client:
                self.client.close()

def json_payload_string(data: Dict[str, Any]) -> str:
    """
    Converts dict response to a standard JSON string.
    """
    return json.dumps(data)
