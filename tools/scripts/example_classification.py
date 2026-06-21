#!/usr/bin/env python3
"""
Phoenix Backup Unknown Application Classification Engine Demonstration Script
"""

import sys
import os
import json

# Adjust path to resolve shared module if run directly from scripts
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from shared.intelligence.classifier import UnknownAppClassifier


def print_header(title: str):
    print("\n" + "=" * 80)
    print(f" {title.upper()}")
    print("=" * 80)


def print_result(package_name: str, app_name: str, permissions: list, metadata: dict, result):
    print(f"\n[+] Inputs:")
    print(f"  - Package Name : {package_name}")
    print(f"  - App Name     : {app_name}")
    print(f"  - Permissions  : {', '.join(permissions) if permissions else 'None'}")
    print(f"  - Metadata     : {json.dumps(metadata)}")
    
    print(f"\n[+] Outputs:")
    print(f"  - Category             : {result.category}")
    print(f"  - Confidence Score     : {result.confidence_score:.2f}")
    print(f"  - Risk Score           : {result.risk_score}/100")
    print(f"  - Recovery Complexity  : {result.recovery_complexity}")
    
    print(f"\n[+] Explainable Decision Log:")
    for idx, exp in enumerate(result.explanations, 1):
        print(f"  {idx}. {exp}")
    print("-" * 80)


def main():
    print_header("Unknown App Classification Engine - Programmatic Example")
    print("[*] Instantiating UnknownAppClassifier...")
    classifier = UnknownAppClassifier()

    # Case 1: Unknown Banking App
    print_header("Case 1: Unrecognized Banking App (with strict security flags)")
    package_name = "com.secure.finance.mobile"
    app_name = "Secure Pay Wallet"
    permissions = ["android.permission.INTERNET", "android.permission.USE_BIOMETRIC"]
    metadata = {"allow_backup": False, "is_system": False, "api_level": 30}
    
    result = classifier.classify_app(package_name, app_name, permissions, metadata)
    print_result(package_name, app_name, permissions, metadata, result)

    # Case 2: Unknown Authenticator App
    print_header("Case 2: Unrecognized Multi-Factor Authenticator App")
    package_name = "org.mfa.token.generator"
    app_name = "Aegis Backup Vault"
    permissions = ["android.permission.CAMERA", "android.permission.USE_BIOMETRIC"]
    metadata = {"allow_backup": True, "is_system": False, "api_level": 31}
    
    result = classifier.classify_app(package_name, app_name, permissions, metadata)
    print_result(package_name, app_name, permissions, metadata, result)

    # Case 3: Unknown System Email Client
    print_header("Case 3: Unrecognized Email App running as a System Package")
    package_name = "com.custom.device.mailer"
    app_name = "System Mailer"
    permissions = ["android.permission.INTERNET", "android.permission.GET_ACCOUNTS"]
    metadata = {"allow_backup": True, "is_system": True, "api_level": 30}
    
    result = classifier.classify_app(package_name, app_name, permissions, metadata)
    print_result(package_name, app_name, permissions, metadata, result)

    # Case 4: Completely Unrecognized App (Fallback to default unknown profile)
    print_header("Case 4: Completely Unrecognized Application (No matches)")
    package_name = "xyz.another.retro.game"
    app_name = "Simple Puzzle Block Game"
    permissions = ["android.permission.VIBRATE"]
    metadata = {"allow_backup": True, "is_system": False, "api_level": 30}
    
    result = classifier.classify_app(package_name, app_name, permissions, metadata)
    print_result(package_name, app_name, permissions, metadata, result)


if __name__ == "__main__":
    main()
