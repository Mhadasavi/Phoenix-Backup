"""
Unit tests for the Recovery Intelligence Rules Loader and Classifier
"""

import os
import tempfile
import unittest
from shared.intelligence.models import AppRuleDefinition
from shared.intelligence.rules import RiskKnowledgeBaseLoader, ApplicationClassifier

class TestIntelligenceRules(unittest.TestCase):

    def setUp(self):
        self.temp_rules = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json", encoding="utf-8")
        self.rules_data = [
            {
                "package_pattern": "com.example.auth",
                "app_name": "Example Authenticator",
                "category": "AUTHENTICATOR",
                "severity": "CRITICAL",
                "reasoning": "TOTP hardware binding keys.",
                "remediation": "Export QR."
            },
            {
                "package_pattern": "com.example.bank.*",
                "app_name": "Example Bank",
                "category": "BANKING",
                "severity": "HIGH",
                "reasoning": "Device binding tokens.",
                "remediation": "Confirm passcode."
            }
        ]
        import json
        json.dump(self.rules_data, self.temp_rules)
        self.temp_rules.close()

    def tearDown(self):
        os.unlink(self.temp_rules.name)

    def test_load_rules_success(self):
        loader = RiskKnowledgeBaseLoader(self.temp_rules.name)
        rules = loader.load_rules()
        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[0].package_pattern, "com.example.auth")
        self.assertEqual(rules[0].category, "AUTHENTICATOR")
        self.assertEqual(rules[1].package_pattern, "com.example.bank.*")

    def test_load_rules_missing_file(self):
        loader = RiskKnowledgeBaseLoader("non_existent_file.json")
        rules = loader.load_rules()
        self.assertEqual(rules, [])

    def test_classifier_exact_match(self):
        loader = RiskKnowledgeBaseLoader(self.temp_rules.name)
        rules = loader.load_rules()
        classifier = ApplicationClassifier(rules)

        match = classifier.match_rule("com.example.auth")
        self.assertIsNotNone(match)
        self.assertEqual(match.app_name, "Example Authenticator")

    def test_classifier_wildcard_match(self):
        loader = RiskKnowledgeBaseLoader(self.temp_rules.name)
        rules = loader.load_rules()
        classifier = ApplicationClassifier(rules)

        match = classifier.match_rule("com.example.bank.app")
        self.assertIsNotNone(match)
        self.assertEqual(match.app_name, "Example Bank")

    def test_classifier_no_match(self):
        loader = RiskKnowledgeBaseLoader(self.temp_rules.name)
        rules = loader.load_rules()
        classifier = ApplicationClassifier(rules)

        match = classifier.match_rule("com.example.calculator")
        self.assertIsNone(match)

if __name__ == "__main__":
    unittest.main()
