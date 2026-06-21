#!/usr/bin/env python3
"""
Phoenix Backup Sprint 2 End-to-End Demo script
"""

import sys
import os
import json
import tempfile
from typing import List, Optional

# Adjust path to resolve shared module if run directly from scripts
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from shared.adb.wrapper import AdbWrapper, AdbDevice
from shared.db.connection import DatabaseConnectionManager
from shared.db.migrations import MigrationRunner
from shared.orchestrator.sprint2_flow import Sprint2Orchestrator
from shared.intelligence.rules import RiskKnowledgeBaseLoader

# Mock AdbWrapper for standalone/offline demonstration execution
class DemoMockAdb(AdbWrapper):
    def __init__(self, serial: str):
        super().__init__()
        self.serial = serial

    def is_adb_available(self) -> bool:
        return True

    def list_devices(self) -> List[AdbDevice]:
        return [AdbDevice(serial=self.serial, status="device", model="Pixel 7 Pro")]

    def get_device_property(self, serial: str, property_name: str) -> Optional[str]:
        if property_name == "ro.product.model":
            return "Pixel 7 Pro"
        if property_name == "ro.build.version.sdk":
            return "33"  # Android 13
        return None

    def execute_shell_command(self, serial: str, command: str, args: Optional[List[str]] = None, timeout: int = 15) -> str:
        args = args or []
        if command == "pm" and "list" in args:
            return (
                "package:/data/app/com.google.android.apps.authenticator2/base.apk=com.google.android.apps.authenticator2\n"
                "package:/data/app/org.thoughtcrime.securesms/base.apk=org.thoughtcrime.securesms\n"
                "package:/data/app/com.example.bank/base.apk=com.example.bank\n"
                "package:/data/app/com.example.social/base.apk=com.example.social\n"
            )
        if command == "dumpsys" and "package" in args:
            pkg = args[1]
            if pkg == "com.example.bank":
                return "  flags=[ HAS_CODE ALLOW_BACKUP ]"
            if pkg == "org.thoughtcrime.securesms":
                return "  flags=[ HAS_CODE ALLOW_BACKUP ]"
            return "  flags=[ HAS_CODE ]"
        if command == "du":
            path = args[-1]
            if path == "/sdcard/DCIM":
                return "25000000\t/sdcard/DCIM"  # ~25GB
            if path == "/sdcard/Pictures":
                return "5000000\t/sdcard/Pictures"   # ~5GB
            if path == "/sdcard/Documents":
                return "500000\t/sdcard/Documents"   # ~500MB
            if path == "/sdcard/Download":
                return "1000000\t/sdcard/Download"   # ~1GB
            return "0\t" + path
        return ""

def main():
    print("======================================================================")
    print("   PHOENIX BACKUP - SPRINT 2 END-TO-END DEMO (OFFLINE ENGINE MVP)")
    print("======================================================================")

    # 1. Setup Temporary Files
    temp_db_file = "phoenix_demo_sprint2.db"
    if os.path.exists(temp_db_file):
        os.remove(temp_db_file)

    # Setup rules JSON path
    rules_path = os.path.join(os.path.dirname(__file__), "../../shared/intelligence/rules.json")
    if not os.path.exists(rules_path):
        # Fallback rules in case it is run from outside root directory
        rules_path = "shared/intelligence/rules.json"

    output_dir = "./demo_reports"
    os.makedirs(output_dir, exist_ok=True)

    print(f"[*] Rules Knowledge Base Source: {rules_path}")
    print(f"[*] Temp Database Target       : {temp_db_file}")
    print(f"[*] Reports Output Destination : {output_dir}")
    print("----------------------------------------------------------------------")

    # Initialize Database & Migrations
    db_manager = DatabaseConnectionManager(temp_db_file)
    print("[*] Running database migrations...")
    with db_manager.get_connection() as conn:
        runner = MigrationRunner(conn)
        runner.run_migrations()

    # Initialize ADB Wrapper (Defaulting to DemoMock for clean standalone running)
    target_serial = "demo-pixel7-987"
    adb_client = DemoMockAdb(target_serial)
    rules_loader = RiskKnowledgeBaseLoader(rules_path)

    # Instantiate the Orchestrator
    orchestrator = Sprint2Orchestrator(
        db_manager=db_manager,
        adb_client=adb_client,
        rules_loader=rules_loader,
        output_dir=output_dir
    )

    print("\n--- PHASE 1: Device Discovery & Connection ---")
    print(f"[*] Connecting to device: {target_serial}...")
    
    print("\n--- PHASE 2 & 3 & 4: Inventory, Classification & Risk Calculation ---")
    print("[*] Crawling app packages...")
    print("[*] Resolving allowBackup configurations via Layered Strategy...")

    print("\n--- PHASE 5: Storage Sizing Auditing ---")
    print("[*] Verifying DCIM, Pictures, Documents, and Download volumes...")

    print("\n--- PHASE 6: Recovery Readiness Evaluation ---")
    print("[*] Compiling checklist tasks and readiness verdicts...")

    # Run the orchestrator audit (simulating one user override)
    user_overrides = ["com.example.bank"]
    assessment = orchestrator.execute_migration_audit(
        serial=target_serial,
        user_overrides=user_overrides
    )

    if not assessment:
        print("[!] Orchestration audit failed.")
        sys.exit(1)

    print("\n--- PHASE 7: Exporting Analysis Report ---")
    report_file = os.path.join(output_dir, "recovery_analysis.json")
    print(f"[+] Exported results to: {report_file}")

    print("\n======================================================================")
    print("                      DEMO ASSESSMENT RESULTS                         ")
    print("======================================================================")
    print(f" Readiness Score : {assessment.readiness_score}/100")
    print(f" Readiness State : {assessment.readiness_state}")
    print(f" Overall Summary : {assessment.overall_assessment}")
    print("----------------------------------------------------------------------")
    
    print("\n[+] System Verdicts:")
    for verdict, ready in assessment.verdicts.items():
        ready_str = "[READY]" if ready else "[NOT READY]"
        print(f"  - {verdict.replace('_ready', '').upper():<10}: {ready_str}")

    print("\n[+] Risk Findings:")
    for finding in assessment.findings:
        res_str = "[OVERRIDDEN/RESOLVED]" if finding.resolved else "[UNRESOLVED]"
        print(f"  * [{finding.severity}] {finding.app_name} ({finding.package_name})")
        print(f"    Reasoning : {finding.reasoning}")
        print(f"    Status    : {res_str}")

    print("\n[+] Actionable Recovery Checklist:")
    for task in assessment.checklist:
        status_str = "[COMPLETED]" if task.status == "COMPLETED" else "[PENDING]"
        print(f"  [{task.priority:<6}] {task.step} ({status_str})")

    print("======================================================================")
    print("[*] Cleaning up temporary demo database...")
    try:
        os.remove(temp_db_file)
    except OSError:
        pass
    print("[*] Demo script run completed.")

if __name__ == "__main__":
    main()
