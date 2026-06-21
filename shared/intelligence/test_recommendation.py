"""
Unit tests for the Recovery Recommendation Engine
"""

import unittest
from shared.intelligence.models import RiskFinding
from shared.intelligence.recommendation import RecoveryRecommendationEngine


class TestRecoveryRecommendationEngine(unittest.TestCase):

    def setUp(self):
        self.engine = RecoveryRecommendationEngine()

    def test_default_sequence_generation(self):
        # Empty inventory, standard device
        findings = []
        inventory = []
        device_info = {"manufacturer": "Google", "model": "Pixel 7", "is_tablet": False}

        sequence = self.engine.generate_sequence(findings, inventory, device_info)

        # Should generate core actions
        self.assertEqual(len(sequence.actions), 2)
        action_ids = [a.action_id for a in sequence.actions]
        self.assertIn("verify_sim", action_ids)
        self.assertIn("verify_google_account", action_ids)
        
        sim_action = next(a for a in sequence.actions if a.action_id == "verify_sim")
        self.assertEqual(sim_action.priority, "CRITICAL")
        self.assertEqual(sim_action.status, "READY")
        self.assertEqual(sequence.blockers_detected, [])

    def test_tablet_device_downgrades_sim_priority(self):
        # Empty inventory, tablet device
        findings = []
        inventory = []
        device_info = {"manufacturer": "Samsung", "model": "Galaxy Tab S8", "is_tablet": True}

        sequence = self.engine.generate_sequence(findings, inventory, device_info)

        sim_action = next(a for a in sequence.actions if a.action_id == "verify_sim")
        self.assertEqual(sim_action.priority, "LOW")
        self.assertIn("Tablet profile detected", sim_action.description)

    def test_topological_sorting_order(self):
        findings = []
        inventory = [
            {"package_name": "com.google.android.apps.authenticator2", "app_name": "Google Authenticator", "category": "AUTHENTICATOR"},
            {"package_name": "com.x8bit.bitwarden", "app_name": "Bitwarden", "category": "PASSWORD_MANAGER"},
            {"package_name": "com.chase.sig.android", "app_name": "Chase Mobile", "category": "BANKING"}
        ]
        device_info = {"model": "Pixel 7"}

        sequence = self.engine.generate_sequence(findings, inventory, device_info)
        
        # Verify sequence length
        self.assertEqual(len(sequence.actions), 5) # 2 core + 3 inventory
        
        # Extract action ids in order
        action_ids = [a.action_id for a in sequence.actions]
        
        # Verify topological ordering constraint
        # verify_google_account must come before authenticator
        # authenticator must come before password manager
        # password manager must come before chase mobile
        google_idx = action_ids.index("verify_google_account")
        auth_idx = action_ids.index("restore_app_com.google.android.apps.authenticator2")
        pw_idx = action_ids.index("restore_app_com.x8bit.bitwarden")
        chase_idx = action_ids.index("restore_app_com.chase.sig.android")
        
        self.assertLess(google_idx, auth_idx)
        self.assertLess(auth_idx, pw_idx)
        self.assertLess(pw_idx, chase_idx)

    def test_cascading_blocker_detection(self):
        # Authenticator has an unresolved risk finding
        findings = [
            RiskFinding(
                package_name="com.google.android.apps.authenticator2",
                app_name="Google Authenticator",
                category="AUTHENTICATOR",
                severity="CRITICAL",
                reasoning="Backup disabled.",
                remediation="Turn on cloud backup.",
                resolved=False
            )
        ]
        inventory = [
            {"package_name": "com.google.android.apps.authenticator2", "app_name": "Google Authenticator", "category": "AUTHENTICATOR"},
            {"package_name": "com.x8bit.bitwarden", "app_name": "Bitwarden", "category": "PASSWORD_MANAGER"},
            {"package_name": "com.chase.sig.android", "app_name": "Chase Mobile", "category": "BANKING"}
        ]
        device_info = {"model": "Pixel 7"}

        sequence = self.engine.generate_sequence(findings, inventory, device_info)

        # Authenticator itself is PENDING because of its unresolved finding
        auth_action = next(a for a in sequence.actions if a.action_id == "restore_app_com.google.android.apps.authenticator2")
        self.assertEqual(auth_action.status, "PENDING")
        self.assertFalse(auth_action.is_blocked)

        # Password Manager is directly BLOCKED by the authenticator
        pw_action = next(a for a in sequence.actions if a.action_id == "restore_app_com.x8bit.bitwarden")
        self.assertEqual(pw_action.status, "BLOCKED")
        self.assertTrue(pw_action.is_blocked)
        self.assertTrue(any("Google Authenticator" in b for b in pw_action.blockers))

        # Banking app is indirectly BLOCKED via the dependency chain (through Password Manager and/or Authenticator)
        chase_action = next(a for a in sequence.actions if a.action_id == "restore_app_com.chase.sig.android")
        self.assertEqual(chase_action.status, "BLOCKED")
        self.assertTrue(chase_action.is_blocked)

        # Ensure global blockers summarize the issue
        self.assertTrue(len(sequence.blockers_detected) > 0)
        self.assertTrue(any("Google Authenticator" in gb for gb in sequence.blockers_detected))

    def test_resolved_findings_do_not_block_downstream(self):
        # Authenticator has a RESOLVED risk finding (e.g. user override applied)
        findings = [
            RiskFinding(
                package_name="com.google.android.apps.authenticator2",
                app_name="Google Authenticator",
                category="AUTHENTICATOR",
                severity="CRITICAL",
                reasoning="Backup disabled.",
                remediation="Turn on cloud backup.",
                resolved=True
            )
        ]
        inventory = [
            {"package_name": "com.google.android.apps.authenticator2", "app_name": "Google Authenticator", "category": "AUTHENTICATOR"},
            {"package_name": "com.x8bit.bitwarden", "app_name": "Bitwarden", "category": "PASSWORD_MANAGER"},
            {"package_name": "com.chase.sig.android", "app_name": "Chase Mobile", "category": "BANKING"}
        ]
        device_info = {"model": "Pixel 7"}

        sequence = self.engine.generate_sequence(findings, inventory, device_info)

        # Authenticator is COMPLETED because the finding is resolved
        auth_action = next(a for a in sequence.actions if a.action_id == "restore_app_com.google.android.apps.authenticator2")
        self.assertEqual(auth_action.status, "COMPLETED")

        # Password Manager and Banking are now READY/COMPLETED, not blocked
        pw_action = next(a for a in sequence.actions if a.action_id == "restore_app_com.x8bit.bitwarden")
        self.assertNotEqual(pw_action.status, "BLOCKED")
        self.assertFalse(pw_action.is_blocked)

        chase_action = next(a for a in sequence.actions if a.action_id == "restore_app_com.chase.sig.android")
        self.assertNotEqual(chase_action.status, "BLOCKED")
        self.assertFalse(chase_action.is_blocked)

        # Global blockers list should be empty
        self.assertEqual(sequence.blockers_detected, [])


if __name__ == "__main__":
    unittest.main()
