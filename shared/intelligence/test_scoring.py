"""
Unit tests for the Recovery Intelligence Scoring Calculator
"""

import unittest
from shared.intelligence.scoring import RiskScoreCalculator, RecoveryReadinessCalculator

class TestIntelligenceScoring(unittest.TestCase):

    def test_app_risk_score_calculation(self):
        # Authenticator with allow_backup=false
        score = RiskScoreCalculator.calculate_app_risk_score(
            category="AUTHENTICATOR",
            allow_backup=False,
            is_system=False
        )
        self.assertEqual(score, 95)  # 80 base + 15 allowBackup
        self.assertEqual(RiskScoreCalculator.derive_risk_level(score), "CRITICAL")

        # Banking app with system profile
        score = RiskScoreCalculator.calculate_app_risk_score(
            category="BANKING",
            allow_backup=True,
            is_system=True
        )
        self.assertEqual(score, 60)  # 70 base - 10 system
        self.assertEqual(RiskScoreCalculator.derive_risk_level(score), "MEDIUM")

    def test_readiness_score_bounds_and_calculations(self):
        # Perfect recovery condition
        score = RecoveryReadinessCalculator.calculate_readiness_score(
            has_contacts=True,
            has_sms=True,
            has_call_logs=True,
            is_tablet=False,
            total_storage_bytes=1000,
            synced_storage_bytes=1000,
            unresolved_penalties=[]
        )
        self.assertEqual(score, 100)  # 45 base + 55 storage

        # Worst condition: locked, no backups
        score = RecoveryReadinessCalculator.calculate_readiness_score(
            has_contacts=False,
            has_sms=False,
            has_call_logs=False,
            is_tablet=False,
            total_storage_bytes=1000,
            synced_storage_bytes=0,
            unresolved_penalties=[20, 20, 20]  # Penalties exceed base
        )
        self.assertEqual(score, 0)  # Clamped to 0

    def test_tablet_dynamic_weight_redistribution(self):
        # Tablet with contacts backed up and full storage sync
        score = RecoveryReadinessCalculator.calculate_readiness_score(
            has_contacts=True,
            has_sms=False,
            has_call_logs=False,
            is_tablet=True,
            total_storage_bytes=1000,
            synced_storage_bytes=1000,
            unresolved_penalties=[]
        )
        self.assertEqual(score, 100)  # 45 base (contacts only) + 55 storage

        # Phone with contacts only (missing SMS/call logs) and full storage sync
        score = RecoveryReadinessCalculator.calculate_readiness_score(
            has_contacts=True,
            has_sms=False,
            has_call_logs=False,
            is_tablet=False,
            total_storage_bytes=1000,
            synced_storage_bytes=1000,
            unresolved_penalties=[]
        )
        self.assertEqual(score, 70)  # 15 base (contacts only) + 55 storage

if __name__ == "__main__":
    unittest.main()
