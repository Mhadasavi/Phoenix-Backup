#!/usr/bin/env python3
"""
Phoenix Backup Historical Backup Comparison Engine Demonstration Script
"""

import sys
import os
import json

# Adjust path to resolve shared module if run directly from scripts
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from shared.db.connection import DatabaseConnectionManager
from shared.db.migrations import MigrationRunner
from shared.db.repositories import DeviceRepository, BackupJobRepository, JobAppInventoryRepository
from shared.intelligence.comparison import BackupComparisonEngine


def print_header(title: str):
    print("\n" + "=" * 80)
    print(f" {title.upper()}")
    print("=" * 80)


def print_comparison_report(report):
    print(f"\n[+] Differential Summary:")
    print(f"  - Device Serial           : {report.device_id}")
    print(f"  - Base Job ID             : {report.base_job_id}")
    print(f"  - Target Job ID           : {report.target_job_id}")
    print(f"  - Base Readiness Score    : {report.base_readiness_score}/100")
    print(f"  - Target Readiness Score  : {report.target_readiness_score}/100")
    
    improved_symbol = "[IMPROVED]" if report.readiness_improved else "[NO IMPROVEMENT]"
    print(f"  - Score Change Delta      : {report.readiness_score_delta:+}pts {improved_symbol}")
    print(f"  - Inventory Size Change   : {report.inventory_size_delta:+} apps")
    print("-" * 80)

    print(f"\n[+] Applications Added (+):")
    if not report.added_apps:
        print("  (None)")
    for app in report.added_apps:
        print(f"  * {app['app_name']} ({app['package_name']}) - Category: {app['category']}, Risk: {app['risk_score']}/100")

    print(f"\n[+] Applications Removed (-):")
    if not report.removed_apps:
        print("  (None)")
    for app in report.removed_apps:
        print(f"  * {app['app_name']} ({app['package_name']}) - Category: {app['category']}, Risk: {app['risk_score']}/100")

    print("-" * 80)
    print(f"\n[!] New Risks Flagged (Escalated or Added High Risks):")
    if not report.new_risks:
        print("  (None)")
    for r in report.new_risks:
        print(f"  * {r['app_name']} ({r['package_name']}) - Category: {r['category']}")
        print(f"    Risk shift : {r['base_risk']} -> {r['target_risk']}")
        print(f"    Trigger    : {r['reason']}")

    print(f"\n[+] Risks Resolved (Reduced or Overridden/Uninstalled):")
    if not report.resolved_risks:
        print("  (None)")
    for r in report.resolved_risks:
        print(f"  * {r['app_name']} ({r['package_name']}) - Category: {r['category']}")
        print(f"    Risk shift : {r['base_risk']} -> {r['target_risk']}")
        print(f"    Trigger    : {r['reason']}")
    print("=" * 80)


def main():
    print_header("Historical Backup Comparison Engine Demo")

    temp_db_file = "phoenix_demo_comparison.db"
    if os.path.exists(temp_db_file):
        try:
            os.remove(temp_db_file)
        except OSError:
            pass

    # 1. Setup DB & Migrations
    db_manager = DatabaseConnectionManager(temp_db_file)
    print("[*] Setting up database and running schema migrations...")
    with db_manager.get_connection() as conn:
        runner = MigrationRunner(conn)
        runner.run_migrations()

    # 2. Setup Device, Jobs and Inventories
    device_id = "comparison-demo-device-999"
    job_1 = "job_baseline_01"
    job_2 = "job_target_02"

    print(f"[*] Ingesting base backup job: {job_1}")
    print(f"[*] Ingesting target backup job: {job_2}")

    with db_manager.get_connection() as conn:
        dev_repo = DeviceRepository(conn)
        job_repo = BackupJobRepository(conn)
        job_app_repo = JobAppInventoryRepository(conn)

        # Save Device
        dev_repo.save_device(device_id, "Google", "Pixel 7 Pro", "13", 33)

        # Base Job (Score 55)
        job_repo.create_job(job_1, device_id, "salt_val", 1000)
        job_repo.update_job_status(job_1, "COMPLETED", 55)

        base_apps = [
            {"package_name": "com.google.android.apps.authenticator2", "app_name": "Google Authenticator", "category": "AUTHENTICATOR", "risk_score": 90, "resolved": 0},
            {"package_name": "com.whatsapp", "app_name": "WhatsApp", "category": "SECURE_MESSENGER", "risk_score": 90, "resolved": 0},
            {"package_name": "com.x8bit.bitwarden", "app_name": "Bitwarden", "category": "PASSWORD_MANAGER", "risk_score": 80, "resolved": 0},
            {"package_name": "com.slack", "app_name": "Slack", "category": "PRODUCTIVITY", "risk_score": 30, "resolved": 0}
        ]
        job_app_repo.save_job_apps(job_1, base_apps)

        # Target Job (Score 85)
        job_repo.create_job(job_2, device_id, "salt_val", 1000)
        job_repo.update_job_status(job_2, "COMPLETED", 85)

        target_apps = [
            # Google Authenticator resolved by user override
            {"package_name": "com.google.android.apps.authenticator2", "app_name": "Google Authenticator", "category": "AUTHENTICATOR", "risk_score": 90, "resolved": 1},
            # WhatsApp uninstalled/removed
            # Bitwarden resolved by user override
            {"package_name": "com.x8bit.bitwarden", "app_name": "Bitwarden", "category": "PASSWORD_MANAGER", "risk_score": 80, "resolved": 1},
            {"package_name": "com.slack", "app_name": "Slack", "category": "PRODUCTIVITY", "risk_score": 30, "resolved": 0},
            # Chase Mobile added as a new application
            {"package_name": "com.chase.sig.android", "app_name": "Chase Mobile", "category": "BANKING", "risk_score": 85, "resolved": 0}
        ]
        job_app_repo.save_job_apps(job_2, target_apps)

    # 3. Perform Comparison
    print("[*] Running differential analysis comparisons...")
    engine = BackupComparisonEngine(db_manager)
    report = engine.compare_jobs(job_1, job_2)

    # 4. Print Report
    print_comparison_report(report)

    # Clean up
    print("[*] Cleaning up temporary comparison database...")
    if os.path.exists(temp_db_file):
        try:
            os.remove(temp_db_file)
        except OSError:
            pass
    print("[*] Demo complete.")


if __name__ == "__main__":
    main()
