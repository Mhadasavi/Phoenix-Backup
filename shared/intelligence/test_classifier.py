"""
Unit tests for the Unknown App Classification Engine
"""

import unittest
from shared.intelligence.classifier import UnknownAppClassifier

class TestUnknownAppClassifier(unittest.TestCase):

    def setUp(self):
        self.classifier = UnknownAppClassifier()

    def test_classify_unknown_banking_app(self):
        package_name = "com.custom.finances.secure"
        app_name = "My Secure Wallet"
        permissions = ["android.permission.INTERNET", "android.permission.USE_BIOMETRIC"]
        metadata = {"allow_backup": False, "is_system": False, "api_level": 30}

        result = self.classifier.classify_app(package_name, app_name, permissions, metadata)

        # Assertions
        self.assertEqual(result.category, "BANKING")
        self.assertGreaterEqual(result.confidence_score, 0.65)
        # Base risk 85 + 15 penalty = 100
        self.assertEqual(result.risk_score, 100)
        self.assertEqual(result.recovery_complexity, "HIGH")
        self.assertTrue(any("allowBackup flag" in exp for exp in result.explanations))

    def test_classify_unknown_authenticator_app(self):
        package_name = "net.auth.vault"
        app_name = "SecToken"
        permissions = ["android.permission.CAMERA"]
        metadata = {"allow_backup": True, "is_system": False, "api_level": 30}

        result = self.classifier.classify_app(package_name, app_name, permissions, metadata)

        self.assertEqual(result.category, "AUTHENTICATOR")
        self.assertEqual(result.recovery_complexity, "CRITICAL")
        self.assertEqual(result.risk_score, 90) # base risk 90

    def test_classify_system_email_app(self):
        package_name = "com.android.email.provider"
        app_name = "System Mailer"
        permissions = ["android.permission.INTERNET", "android.permission.GET_ACCOUNTS"]
        metadata = {"allow_backup": True, "is_system": True, "api_level": 30}

        result = self.classifier.classify_app(package_name, app_name, permissions, metadata)

        self.assertEqual(result.category, "EMAIL")
        # Base risk 30 - 20 system discount = 10
        self.assertEqual(result.risk_score, 10)
        self.assertEqual(result.recovery_complexity, "LOW")

    def test_classify_completely_unknown_app(self):
        package_name = "xyz.another.game"
        app_name = "Simple Puzzle Game"
        permissions = ["android.permission.VIBRATE"]
        metadata = {"allow_backup": True, "is_system": False, "api_level": 30}

        result = self.classifier.classify_app(package_name, app_name, permissions, metadata)

        self.assertEqual(result.category, "UNKNOWN_APP")
        self.assertEqual(result.confidence_score, 0.5)
        self.assertEqual(result.risk_score, 30) # base fallback risk

if __name__ == "__main__":
    unittest.main()
