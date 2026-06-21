#!/usr/bin/env python3
"""
Phoenix Backup Sprint 3 Integrated Backup CLI Runner
"""

import argparse
import sys
import os
import json

# Adjust path to resolve shared module if run directly from scripts
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from shared.db.connection import DatabaseConnectionManager
from shared.db.migrations import MigrationRunner
from shared.db.import_service import BackupImportService
from shared.orchestrator.backup_runner import BackupRunner

def main():
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True
    )
    
    parser = argparse.ArgumentParser(description="Phoenix Backup Sprint 3 Data Extraction Runner")
    parser.add_argument("--serial", required=True, help="Android device serial number")
    parser.add_argument("--db", default="phoenix_local.db", help="SQLite database target path")
    parser.add_argument("--output", required=True, help="Output directory for reports and sync directories")
    parser.add_argument("--token", required=True, help="Secure transport authentication token")
    parser.add_argument("--port", type=int, default=50051, help="Secure transport server port")

    args = parser.parse_args()

    # Resolve database path
    db_path = os.path.abspath(args.db)

    # 1. Initialize DB Connection, run migrations, and bootstrap import tables
    db_manager = DatabaseConnectionManager(db_path)
    try:
        with db_manager.get_connection() as conn:
            # Run DDL migrations
            migrator = MigrationRunner(conn)
            migrator.run_migrations()
            
            # Bootstrap Backup Import Service tables (job_contacts, etc.)
            BackupImportService(conn)
    except Exception as db_err:
        print(json.dumps({"success": False, "error": f"Database setup failed: {db_err}"}))
        sys.exit(1)

    # 2. Run the backup extraction orchestrator
    try:
        with db_manager.get_connection() as conn:
            runner = BackupRunner(conn, token=args.token, port=args.port)
            job_id = runner.execute_backup(serial=args.serial)
            
            if job_id:
                print(json.dumps({
                    "success": True,
                    "job_id": job_id,
                    "message": "Full backup extraction completed successfully."
                }))
                sys.exit(0)
            else:
                print(json.dumps({
                    "success": False,
                    "error": "Backup extraction runner returned failure. Check log outputs."
                }))
                sys.exit(1)
    except Exception as e:
        print(json.dumps({"success": False, "error": f"Unexpected backup script exception: {e}"}))
        sys.exit(1)

if __name__ == "__main__":
    main()
