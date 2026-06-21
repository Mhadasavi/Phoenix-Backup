"""
Phoenix Backup SQLite Schema Migrations Coordinator
"""

import logging
import sqlite3
from typing import List

logger = logging.getLogger("phoenix.db.migrations")

# Sprint 1 SQL Migration scripts
MIGRATION_SCRIPTS: List[str] = [
    # Version 1 DDL schemas (Sprint 1 core tables)
    """
    CREATE TABLE IF NOT EXISTS devices (
        device_id TEXT PRIMARY KEY,
        manufacturer TEXT NOT NULL,
        model TEXT NOT NULL,
        android_version TEXT NOT NULL,
        api_level INTEGER NOT NULL,
        first_seen DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_seen DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS backup_jobs (
        job_id TEXT PRIMARY KEY,
        device_id TEXT NOT NULL,
        start_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        end_time DATETIME,
        status TEXT NOT NULL CHECK(status IN ('STARTED', 'COMPLETED', 'FAILED', 'PARTIAL')),
        readiness_score INTEGER CHECK(readiness_score >= 0 AND readiness_score <= 100),
        encryption_salt TEXT NOT NULL,
        key_derivation_rounds INTEGER NOT NULL,
        FOREIGN KEY(device_id) REFERENCES devices(device_id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        log_level TEXT NOT NULL CHECK(log_level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'FATAL')),
        module TEXT NOT NULL,
        message TEXT NOT NULL
    );
    """,
    # Version 4 Optimization Indexes
    """
    CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
    """,
    # Version 5 Sprint 2 Recovery Intelligence Schemas
    """
    CREATE TABLE IF NOT EXISTS device_app_inventory (
        device_id TEXT NOT NULL,
        package_name TEXT NOT NULL,
        app_name TEXT NOT NULL,
        version_name TEXT,
        version_code INTEGER,
        apk_path TEXT,
        is_system INTEGER NOT NULL CHECK(is_system IN (0, 1)),
        allow_backup INTEGER NOT NULL CHECK(allow_backup IN (0, 1)) DEFAULT 1,
        backup_source TEXT NOT NULL CHECK(backup_source IN ('RULE_MATCH', 'HEURISTIC_API', 'DUMPSYS_RESOLVED')),
        PRIMARY KEY(device_id, package_name),
        FOREIGN KEY(device_id) REFERENCES devices(device_id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS device_storage_manifest (
        device_id TEXT NOT NULL,
        directory_path TEXT NOT NULL,
        total_bytes INTEGER NOT NULL,
        synced_bytes INTEGER NOT NULL DEFAULT 0,
        last_verified DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(device_id, directory_path),
        FOREIGN KEY(device_id) REFERENCES devices(device_id) ON DELETE CASCADE
    );
    """,
    # Version 6 DDL Schema (Historical App Inventories)
    """
    CREATE TABLE IF NOT EXISTS job_app_inventory (
        job_id TEXT NOT NULL,
        package_name TEXT NOT NULL,
        app_name TEXT NOT NULL,
        version_name TEXT,
        version_code INTEGER,
        apk_path TEXT,
        is_system INTEGER NOT NULL CHECK(is_system IN (0, 1)),
        allow_backup INTEGER NOT NULL CHECK(allow_backup IN (0, 1)) DEFAULT 1,
        category TEXT NOT NULL,
        risk_score INTEGER NOT NULL,
        resolved INTEGER NOT NULL CHECK(resolved IN (0, 1)) DEFAULT 0,
        PRIMARY KEY(job_id, package_name),
        FOREIGN KEY(job_id) REFERENCES backup_jobs(job_id) ON DELETE CASCADE
    );
    """
]

class MigrationRunner:
    """
    Manages relational table installations and schemas versions updates.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def run_migrations(self) -> int:
        """
        Executes pending migration script segments. Returns total migrations applied.
        """
        logger.info("Initializing schema version audits...")
        
        # Setup migrations tracking table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Upgrade check for backup_jobs schema mismatch (Node.js vs Python schema conflict)
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='backup_jobs';")
        if cursor.fetchone():
            cursor_info = self.conn.execute("PRAGMA table_info(backup_jobs);")
            columns = [row[1] for row in cursor_info.fetchall()]
            if "readiness_score" not in columns:
                logger.info("Upgrading backup_jobs schema for Sprint 2.5 support...")
                try:
                    self.conn.execute("ALTER TABLE backup_jobs RENAME TO backup_jobs_old;")
                    self.conn.execute("""
                    CREATE TABLE backup_jobs (
                        job_id TEXT PRIMARY KEY,
                        device_id TEXT NOT NULL,
                        start_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        end_time DATETIME,
                        status TEXT NOT NULL CHECK(status IN ('STARTED', 'COMPLETED', 'FAILED', 'PARTIAL')),
                        readiness_score INTEGER CHECK(readiness_score >= 0 AND readiness_score <= 100),
                        encryption_salt TEXT NOT NULL,
                        key_derivation_rounds INTEGER NOT NULL,
                        FOREIGN KEY(device_id) REFERENCES devices(device_id) ON DELETE CASCADE
                    );
                    """)
                    self.conn.execute("""
                    INSERT INTO backup_jobs (job_id, device_id, start_time, end_time, status, encryption_salt, key_derivation_rounds)
                    SELECT job_id, device_id, start_time, end_time, status, encryption_salt, key_derivation_rounds FROM backup_jobs_old;
                    """)
                    
                    # Rebuild job_app_inventory if it exists to repair its foreign key constraint referencing backup_jobs_old
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='job_app_inventory';")
                    if cursor.fetchone():
                        logger.info("Rebuilding job_app_inventory to repair foreign key reference...")
                        self.conn.execute("ALTER TABLE job_app_inventory RENAME TO job_app_inventory_old;")
                        self.conn.execute("""
                        CREATE TABLE job_app_inventory (
                            job_id TEXT NOT NULL,
                            package_name TEXT NOT NULL,
                            app_name TEXT NOT NULL,
                            version_name TEXT,
                            version_code INTEGER,
                            apk_path TEXT,
                            is_system INTEGER NOT NULL CHECK(is_system IN (0, 1)),
                            allow_backup INTEGER NOT NULL CHECK(allow_backup IN (0, 1)) DEFAULT 1,
                            category TEXT NOT NULL,
                            risk_score INTEGER NOT NULL,
                            resolved INTEGER NOT NULL CHECK(resolved IN (0, 1)) DEFAULT 0,
                            PRIMARY KEY(job_id, package_name),
                            FOREIGN KEY(job_id) REFERENCES backup_jobs(job_id) ON DELETE CASCADE
                        );
                        """)
                        self.conn.execute("""
                        INSERT INTO job_app_inventory (
                            job_id, package_name, app_name, version_name, version_code, 
                            apk_path, is_system, allow_backup, category, risk_score, resolved
                        )
                        SELECT 
                            job_id, package_name, app_name, version_name, version_code, 
                            apk_path, is_system, allow_backup, category, risk_score, resolved 
                        FROM job_app_inventory_old;
                        """)
                        self.conn.execute("DROP TABLE job_app_inventory_old;")

                    self.conn.execute("DROP TABLE backup_jobs_old;")
                    logger.info("Successfully upgraded backup_jobs schema to include readiness_score.")
                except Exception as upgrade_err:
                    logger.error("Failed upgrading backup_jobs schema: %s", upgrade_err)

        # Get current schema version
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(version) FROM schema_migrations;")
        row = cursor.fetchone()
        current_version = row[0] if row and row[0] is not None else 0
        logger.debug("Current database schema version resolved to: %d", current_version)

        applied_count = 0
        
        # Apply version increments sequentially
        for index, sql in enumerate(MIGRATION_SCRIPTS):
            target_version = index + 1
            if target_version > current_version:
                logger.info("Applying database migration segment version %d...", target_version)
                try:
                    # Run schema statements
                    self.conn.execute(sql)
                    # Write schema migration log
                    self.conn.execute(
                        "INSERT INTO schema_migrations (version) VALUES (?);", 
                        (target_version,)
                    )
                    applied_count += 1
                except sqlite3.Error as err:
                    logger.error("Failed executing migration version %d: %s", target_version, err)
                    raise err

        logger.info("Database schemas validation finished. Applied %d updates.", applied_count)
        return applied_count
