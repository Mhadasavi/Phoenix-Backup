"""
Phoenix Backup MVP Orchestration Flow
"""

import logging
import uuid
from typing import Optional
from shared.adb.wrapper import AdbClientInterface
from shared.discovery.detector import DeviceDetector, AndroidDevice
from shared.inventory.manager import AppInventoryManager
from shared.db.connection import DatabaseConnectionManager
from shared.db.repositories import DeviceRepository, BackupJobRepository, AuditLogRepository
from shared.export.csv_exporter import CsvExporter

# Configure module-level logger
logger = logging.getLogger("phoenix.orchestrator")

class MvpOrchestrator:
    """
    Coordinates the Sprint 1 MVP pipeline:
    Detect Device -> Save Device to SQLite -> Start Job -> Scan Apps -> Export CSV -> Complete Job.
    """

    def __init__(
        self,
        db_manager: DatabaseConnectionManager,
        adb_client: AdbClientInterface,
        output_dir: str
    ):
        self.db_manager = db_manager
        self.adb_client = adb_client
        self.exporter = CsvExporter(output_dir)

    def execute_migration_audit(self, serial: str) -> bool:
        """
        Executes the complete migration audit workflow.
        Returns True on success, False if any step fails.
        """
        job_id = str(uuid.uuid4())
        logger.info("Initiating MVP migration audit. Job ID: %s", job_id)

        try:
            # 1. Detect Device Details
            detector = DeviceDetector(self.adb_client)
            devices = detector.detect_devices()
            target_device = next((d for d in devices if d.serial == serial), None)

            if not target_device:
                logger.error("Target device [%s] not detected during audit.", serial)
                self._write_audit_log("ERROR", "ORCHESTRATOR", f"Device {serial} not detected.")
                return False

            if target_device.status != "device":
                logger.error("Target device [%s] status is '%s'. Cannot execute scan.", serial, target_device.status)
                self._write_audit_log("ERROR", "ORCHESTRATOR", f"Device status is '{target_device.status}'.")
                return False

            # 2. Persist Device and Start Job in SQLite (Atomic Write Transaction)
            logger.info("Persisting device metadata and job status to SQLite...")
            with self.db_manager.get_connection() as conn:
                device_repo = DeviceRepository(conn)
                job_repo = BackupJobRepository(conn)
                audit_repo = AuditLogRepository(conn)

                # Save device
                device_repo.save_device(
                    device_id=target_device.serial,
                    manufacturer=target_device.manufacturer or "Unknown",
                    model=target_device.model or "Unknown",
                    android_version=target_device.android_version or "Unknown",
                    api_level=target_device.api_level or 0
                )

                # Initialize backup job (Generate mock salt for PBKDF2/Argon2 key mapping)
                job_repo.create_job(
                    job_id=job_id,
                    device_id=target_device.serial,
                    salt="mvp_derivation_salt_val",
                    rounds=100000
                )
                
                audit_repo.log("INFO", "ORCHESTRATOR", f"Job {job_id} started successfully.")

            # 3. Scan Installed Applications
            inventory_manager = AppInventoryManager(self.adb_client)
            # Fetch versions is enabled here since this is the actual execution flow
            apps = inventory_manager.get_installed_apps(serial=serial, include_system=False, fetch_versions=True)

            # 4. Export CSV Reports (Writes Atomically)
            logger.info("Compiling and writing CSV reports...")
            device_csv_name = f"device_summary_{serial}.csv"
            apps_csv_name = f"apps_inventory_{serial}.csv"

            # Export Device Info CSV
            self.exporter.export_device_info(device_csv_name, target_device)
            # Export Tabular App List CSV
            self.exporter.export_app_inventory(apps_csv_name, apps)

            # 5. Mark Job as Completed in SQLite
            logger.info("Finalizing backup job status...")
            with self.db_manager.get_connection() as conn:
                job_repo = BackupJobRepository(conn)
                audit_repo = AuditLogRepository(conn)

                # Update job to COMPLETED (Mock readiness score to 100 for Sprint 1 baseline)
                job_repo.update_job_status(job_id=job_id, status="COMPLETED", score=100)
                audit_repo.log("INFO", "ORCHESTRATOR", f"Job {job_id} completed successfully.")

            logger.info("MVP Migration Audit pipeline executed successfully.")
            return True

        except Exception as err:
            logger.error("Audit pipeline execution failed: %s", err)
            self._write_audit_log("FATAL", "ORCHESTRATOR", f"Pipeline crashed: {err}")
            
            # Attempt to mark job as FAILED
            try:
                with self.db_manager.get_connection() as conn:
                    job_repo = BackupJobRepository(conn)
                    job_repo.update_job_status(job_id=job_id, status="FAILED")
            except Exception as db_err:
                logger.debug("Failed updating job fail status: %s", db_err)
            
            return False

    def _write_audit_log(self, level: str, module: str, message: str) -> None:
        """Helper to write log records to SQLite database."""
        try:
            with self.db_manager.get_connection() as conn:
                audit_repo = AuditLogRepository(conn)
                audit_repo.log(level, module, message)
        except Exception as err:
            logger.debug("Failed to write database audit log: %s", err)
