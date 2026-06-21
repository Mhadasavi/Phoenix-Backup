"""
Unit tests for the Findings Engine Module
"""

import unittest
from unittest.mock import MagicMock
from shared.intelligence.models import AppRuleDefinition
from shared.intelligence.rules import ApplicationClassifier
from shared.intelligence.findings import FindingsEngine

class TestFindingsEngine(unittest.TestCase):

    def setUp(self):
        # Setup mock classifier
        self.mock_classifier = MagicMock()
        self.engine = FindingsEngine(self.mock_classifier)

    def test_compile_findings_and_checklist_with_rule(self):
        # 1. Mock rule match
        rule = AppRuleDefinition(
            package_pattern="com.example.messenger",
            app_name="Example Messenger",
            category="SECURE_MESSENGER",
            severity="CRITICAL",
            reasoning="Local SQLCipher DB.",
            remediation="Enable chat backups in settings."
        )
        self.mock_classifier.match_rule.return_value = rule

        # 2. Scanned apps input
        db_apps = [
            {
                "package_name": "com.example.messenger",
                "app_name": "Example Messenger",
                "is_system": False,
                "allow_backup": False
            }
        ]

        findings, checklist, penalties = self.engine.compile_findings_and_checklist(db_apps, [])

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "CRITICAL")
        self.assertEqual(findings[0].resolved, False)
        
        self.assertEqual(len(checklist), 1)
        self.assertEqual(checklist[0].priority, "MUST")
        self.assertEqual(checklist[0].status, "PENDING")
        self.assertEqual(penalties, [20])  # Critical penalty

    def test_compile_findings_and_checklist_with_user_override(self):
        rule = AppRuleDefinition(
            package_pattern="com.example.bank",
            app_name="Example Bank",
            category="BANKING",
            severity="HIGH",
            reasoning="Device bindings.",
            remediation="Confirm credentials."
        )
        self.mock_classifier.match_rule.return_value = rule

        db_apps = [
            {
                "package_name": "com.example.bank",
                "app_name": "Example Bank",
                "is_system": False,
                "allow_backup": True
            }
        ]

        # User overrides acknowledging this app is secured
        findings, checklist, penalties = self.engine.compile_findings_and_checklist(
            db_apps, 
            ["com.example.bank"]
        )

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].resolved, True)
        
        self.assertEqual(len(checklist), 1)
        self.assertEqual(checklist[0].status, "COMPLETED")
        self.assertEqual(penalties, [])  # No active penalties

    def test_generate_remediation_summary(self):
        from shared.intelligence.models import RiskFinding
        findings = [
            RiskFinding("com.pkg.a", "App A", "AUTHENTICATOR", "CRITICAL", "reason", "step", resolved=False),
            RiskFinding("com.pkg.b", "App B", "BANKING", "HIGH", "reason", "step", resolved=True),
            RiskFinding("com.pkg.c", "App C", "LOCAL_DATA", "MEDIUM", "reason", "step", resolved=False)
        ]

        summary = self.engine.generate_remediation_summary(findings)

        self.assertEqual(summary["total_risks_count"], 3)
        self.assertEqual(summary["unresolved_risks_count"], 2)
        self.assertEqual(summary["resolved_risks_count"], 1)
        self.assertEqual(summary["critical_unresolved_count"], 1)
        self.assertEqual(summary["high_unresolved_count"], 0)  # App B was resolved
        self.assertEqual(summary["medium_unresolved_count"], 1)

if __name__ == "__main__":
    unittest.main()
