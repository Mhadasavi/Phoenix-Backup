#!/usr/bin/env python3
"""
Phoenix Backup Sidecar Command Line Interface (CLI Entry)
"""

import argparse
import sys
import os

# Adjust path to resolve shared module if run directly from scripts
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from shared.adb.wrapper import AdbWrapper
from shared.db.connection import DatabaseConnectionManager
from shared.db.migrations import MigrationRunner
from shared.orchestrator.flow import MvpOrchestrator

def main():
    parser = argparse.ArgumentParser(description="Phoenix Backup Offline Migration Core CLI")
    parser.add_argument("--serial", required=True, help="Android device serial number")
    parser.add_argument("--db", default="phoenix_local.db", help="SQLite database target path")
    parser.add_argument("--output", default="./reports", help="Output directory for generated CSV files")
    
    args = parser.parse_args()

    print(f"[*] Initializing Phoenix Backup Core Sidecar...")
    print(f"[*] Target Serial: {args.serial}")
    print(f"[*] Target DB    : {args.db}")
    print(f"[*] Output Dir   : {args.output}")

    # 1. Initialize DB Connection and apply migrations
    db_manager = DatabaseConnectionManager(args.db)
    try:
        with db_manager.get_connection() as conn:
            migrator = MigrationRunner(conn)
            migrator.run_migrations()
    except Exception as db_err:
        print(f"[!] Database initialization failure: {db_err}", file=sys.stderr)
        sys.exit(1)

    # 2. Initialize Adb Wrapper
    try:
        adb_client = AdbWrapper()
    except Exception as adb_err:
        print(f"[!] ADB initialization failure: {adb_err}", file=sys.stderr)
        sys.exit(1)

    # 3. Initialize Orchestrator and run the audit
    orchestrator = MvpOrchestrator(
        db_manager=db_manager,
        adb_client=adb_client,
        output_dir=args.output
    )

    success = orchestrator.execute_migration_audit(args.serial)
    if success:
        print("[*] Migration audit pipeline completed successfully.")
        sys.exit(0)
    else:
        print("[!] Migration audit pipeline encountered an error.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
