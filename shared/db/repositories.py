"""
Phoenix Backup Repositories (Data Access Layer)
"""

import sqlite3
from typing import List, Optional, Dict, Any

class DeviceRepository:
    """
    Handles SQLite transactions for Android device logs.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save_device(self, device_id: str, manufacturer: str, model: str, android_version: str, api_level: int) -> None:
        """
        Inserts or updates device records. Updates the 'last_seen' timestamp.
        """
        sql = """
            INSERT INTO devices (device_id, manufacturer, model, android_version, api_level)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                android_version = excluded.android_version,
                api_level = excluded.api_level,
                last_seen = CURRENT_TIMESTAMP;
        """
        self.conn.execute(sql, (device_id, manufacturer, model, android_version, api_level))

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves device details. Returns None if device_id is not found.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM devices WHERE device_id = ?;", (device_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


class BackupJobRepository:
    """
    Handles SQL configurations for active backup transaction processes.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_job(self, job_id: str, device_id: str, salt: str, rounds: int) -> None:
        """
        Creates a new backup job marked as 'STARTED'.
        """
        sql = """
            INSERT INTO backup_jobs (job_id, device_id, status, encryption_salt, key_derivation_rounds)
            VALUES (?, ?, 'STARTED', ?, ?);
        """
        self.conn.execute(sql, (job_id, device_id, salt, rounds))

    def update_job_status(self, job_id: str, status: str, score: Optional[int] = None) -> None:
        """
        Updates status metrics and records job completion times on success or failure.
        """
        sql = """
            UPDATE backup_jobs 
            SET status = ?, 
                readiness_score = COALESCE(?, readiness_score),
                end_time = CASE WHEN ? IN ('COMPLETED', 'FAILED') THEN CURRENT_TIMESTAMP ELSE end_time END
            WHERE job_id = ?;
        """
        self.conn.execute(sql, (status, score, status, job_id))

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves job history parameters.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM backup_jobs WHERE job_id = ?;", (job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


class AuditLogRepository:
    """
    Relational logger repository. Writes to 'audit_logs' table.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def log(self, level: str, module: str, message: str) -> None:
        """
        Writes logs directly to SQLite audit tables.
        """
        sql = """
            INSERT INTO audit_logs (log_level, module, message)
            VALUES (?, ?, ?);
        """
        self.conn.execute(sql, (level, module, message))

    def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieves logs ordered by execution timestamps.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?;", (limit,))
        return [dict(row) for row in cursor.fetchall()]


class AppInventoryRepository:
    """
    Handles SQLite transactions for the Android device application inventory.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save_app(
        self,
        device_id: str,
        package_name: str,
        app_name: str,
        version_name: Optional[str],
        version_code: Optional[int],
        apk_path: str,
        is_system: bool,
        allow_backup: bool,
        backup_source: str
    ) -> None:
        """
        Upsert a device package record.
        """
        sql = """
            INSERT INTO device_app_inventory (
                device_id, package_name, app_name, version_name, 
                version_code, apk_path, is_system, allow_backup, backup_source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(device_id, package_name) DO UPDATE SET
                app_name = excluded.app_name,
                version_name = excluded.version_name,
                version_code = excluded.version_code,
                apk_path = excluded.apk_path,
                is_system = excluded.is_system,
                allow_backup = excluded.allow_backup,
                backup_source = excluded.backup_source;
        """
        self.conn.execute(
            sql,
            (
                device_id,
                package_name,
                app_name,
                version_name,
                version_code,
                apk_path,
                1 if is_system else 0,
                1 if allow_backup else 0,
                backup_source
            )
        )

    def get_apps_for_device(self, device_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all application records for a specific device.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM device_app_inventory WHERE device_id = ?;", (device_id,))
        return [dict(row) for row in cursor.fetchall()]


class StorageManifestRepository:
    """
    Handles SQLite configurations for media storage sync metrics.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save_directory_manifest(
        self,
        device_id: str,
        directory_path: str,
        total_bytes: int,
        synced_bytes: int
    ) -> None:
        """
        Upsert a storage manifest entry for a directory.
        """
        sql = """
            INSERT INTO device_storage_manifest (
                device_id, directory_path, total_bytes, synced_bytes, last_verified
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(device_id, directory_path) DO UPDATE SET
                total_bytes = excluded.total_bytes,
                synced_bytes = excluded.synced_bytes,
                last_verified = CURRENT_TIMESTAMP;
        """
        self.conn.execute(sql, (device_id, directory_path, total_bytes, synced_bytes))

    def get_storage_manifest_for_device(self, device_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all storage sync definitions for a device.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM device_storage_manifest WHERE device_id = ?;", (device_id,))
        return [dict(row) for row in cursor.fetchall()]


class JobAppInventoryRepository:
    """
    Handles historical app snapshots linked to specific backup jobs.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save_job_apps(self, job_id: str, apps: List[Dict[str, Any]]) -> None:
        """
        Saves a collection of app records for a job.
        """
        sql = """
            INSERT OR REPLACE INTO job_app_inventory (
                job_id, package_name, app_name, version_name, 
                version_code, apk_path, is_system, allow_backup, 
                category, risk_score, resolved
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        for app in apps:
            self.conn.execute(
                sql,
                (
                    job_id,
                    app["package_name"],
                    app["app_name"],
                    app.get("version_name"),
                    app.get("version_code"),
                    app.get("apk_path"),
                    1 if app.get("is_system") else 0,
                    1 if app.get("allow_backup", True) else 0,
                    app.get("category", "Unknown"),
                    int(app.get("risk_score", 0)),
                    1 if app.get("resolved") else 0
                )
            )

    def get_apps_for_job(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all application records snapshotted for a specific job.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM job_app_inventory WHERE job_id = ?;", (job_id,))
        return [dict(row) for row in cursor.fetchall()]

