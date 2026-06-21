#!/usr/bin/env python3
"""
Phoenix Backup Recovery Recommendation Engine Demonstration Script
"""

import sys
import os
import json

# Adjust path to resolve shared module if run directly from scripts
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from shared.intelligence.models import RiskFinding
from shared.intelligence.recommendation import RecoveryRecommendationEngine


def print_header(title: str):
    print("\n" + "=" * 80)
    print(f" {title.upper()}")
    print("=" * 80)


def print_sequence(sequence):
    print("\n[+] Recovery Sequence (Topologically Sorted):")
    for idx, action in enumerate(sequence.actions, 1):
        status_symbol = "[READY]"
        if action.status == "COMPLETED":
            status_symbol = "[COMPLETED]"
        elif action.status == "BLOCKED":
            status_symbol = "[BLOCKED]"
        elif action.status == "PENDING":
            status_symbol = "[PENDING (Needs Action)]"

        print(f"  {idx:<2}. {status_symbol:<22} | {action.title} ({action.priority})")
        print(f"      Category    : {action.category}")
        print(f"      Description : {action.description}")
        if action.depends_on:
            print(f"      Depends On  : {', '.join(action.depends_on)}")
        if action.is_blocked:
            print(f"      BLOCKERS DETECTED:")
            for b in action.blockers:
                print(f"        * {b}")
        print()

    if sequence.blockers_detected:
        print("-" * 80)
        print("[!] Global Blockers Detected (Must resolve these first):")
        for idx, gb in enumerate(sequence.blockers_detected, 1):
            print(f"  {idx}. {gb}")
        print("-" * 80)


def main():
    print_header("Recovery Recommendation Engine Demo")
    engine = RecoveryRecommendationEngine()

    # Case 1: Standard Phone with No Blockers (All findings resolved/overridden)
    print_header("Scenario 1: Standard Device with No Unresolved Blockers")
    device_info = {"manufacturer": "Google", "model": "Pixel 7 Pro", "is_tablet": False}
    inventory = [
        {"package_name": "com.google.android.apps.authenticator2", "app_name": "Google Authenticator", "category": "AUTHENTICATOR"},
        {"package_name": "com.x8bit.bitwarden", "app_name": "Bitwarden", "category": "PASSWORD_MANAGER"},
        {"package_name": "com.chase.sig.android", "app_name": "Chase Mobile", "category": "BANKING"},
        {"package_name": "org.thoughtcrime.securesms", "app_name": "Signal", "category": "SECURE_MESSENGER"}
    ]
    # Finding exists but is marked as RESOLVED (e.g. user performed manual sync/export)
    findings = [
        RiskFinding(
            package_name="com.google.android.apps.authenticator2",
            app_name="Google Authenticator",
            category="AUTHENTICATOR",
            severity="CRITICAL",
            reasoning="Enforces Keystore hardware binds.",
            remediation="Export backup QR code.",
            resolved=True
        )
    ]

    sequence = engine.generate_sequence(findings, inventory, device_info)
    print_sequence(sequence)

    # Case 2: Blocker Cascading Scenario (Google Authenticator backup is unresolved)
    print_header("Scenario 2: Blocker Cascading (Unresolved Authenticator Backup)")
    device_info = {"manufacturer": "Samsung", "model": "Galaxy S23", "is_tablet": False}
    # Finding is NOT resolved
    findings = [
        RiskFinding(
            package_name="com.google.android.apps.authenticator2",
            app_name="Google Authenticator",
            category="AUTHENTICATOR",
            severity="CRITICAL",
            reasoning="Enforces Keystore hardware binds. standard backups disabled.",
            remediation="Open Authenticator -> Export accounts QR code.",
            resolved=False
        )
    ]

    sequence = engine.generate_sequence(findings, inventory, device_info)
    print_sequence(sequence)

    # Case 3: Tablet Device (Downgraded SIM dependency)
    print_header("Scenario 3: Tablet Device (Downgrades SIM requirement to LOW)")
    device_info = {"manufacturer": "Lenovo", "model": "Yoga Tab 13", "is_tablet": True}
    inventory = [
        {"package_name": "com.x8bit.bitwarden", "app_name": "Bitwarden", "category": "PASSWORD_MANAGER"}
    ]
    findings = []

    sequence = engine.generate_sequence(findings, inventory, device_info)
    print_sequence(sequence)


if __name__ == "__main__":
    main()
