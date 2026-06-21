"""
Phoenix Backup Recovery Readiness and Risk Scoring Engine (Hardened Python Implementation)
"""

import logging
from typing import List

logger = logging.getLogger("phoenix.intelligence.scoring")

class RiskScoreCalculator:
    """
    Computes qualitative risk levels and quantitative scores (0-100) for applications.
    """

    @staticmethod
    def calculate_app_risk_score(
        category: str,
        allow_backup: bool,
        is_system: bool,
        has_device_admin: bool = False,
        has_accessibility: bool = False
    ) -> int:
        """
        Calculates a risk score from 0 to 100 based on category, backup capabilities,
        and system integration permissions.
        """
        # Base category values
        base_scores = {
            "AUTHENTICATOR": 80,
            "SECURE_MESSENGER": 80,
            "PASSWORD_MANAGER": 70,
            "BANKING": 70,
            "UPI": 70,
            "LOCAL_DATA_APP": 50,
            "GALLERY": 50,
            "VPN": 45,
            "GAMING": 30,
            "SOCIAL_MEDIA": 20,
            "PRODUCTIVITY": 20,
            "EMAIL": 20,
            "LAUNCHER": 15,
            "SYSTEM_UTILITY": 15
        }
        
        score = base_scores.get(category, 20)  # Default for Unknown is 20
        
        if not allow_backup:
            score += 15
            
        if has_device_admin:
            score += 10
        if has_accessibility:
            score += 10
            
        # System applications generally have low recovery risk since they are preloaded
        if is_system:
            score -= 10
            
        return min(100, max(0, score))

    @staticmethod
    def derive_risk_level(score: int) -> str:
        """Maps quantitative risk score to threat severity level classification."""
        if score >= 85:
            return "CRITICAL"
        elif score >= 70:
            return "HIGH"
        elif score >= 40:
            return "MEDIUM"
        return "LOW"


class RecoveryReadinessCalculator:
    """
    Computes overall device recovery readiness scores incorporating base backups,
    media synchronization percentages, and outstanding unresolved application threats.
    """

    @staticmethod
    def calculate_readiness_score(
        has_contacts: bool,
        has_sms: bool,
        has_call_logs: bool,
        is_tablet: bool,
        total_storage_bytes: int,
        synced_storage_bytes: int,
        unresolved_penalties: List[int]
    ) -> int:
        """
        Executes the scoring formula:
        S = S_base + S_storage - Sum(Penalties)
        """
        # 1. Base Backups (Max: 45 pts)
        if is_tablet:
            # Tablet redistribution: no cellular capabilities expected
            # Contacts = 100% of core score (45 pts)
            s_base = 45 if has_contacts else 0
        else:
            # Normal: Contacts = 15, SMS = 15, Call Logs = 15
            s_base = 0
            if has_contacts:
                s_base += 15
            if has_sms:
                s_base += 15
            if has_call_logs:
                s_base += 15

        # 2. Storage Sync (Max: 55 pts)
        if total_storage_bytes <= 0:
            s_storage = 55  # Default to full score if no storage to sync
        else:
            ratio = min(1.0, max(0.0, synced_storage_bytes / total_storage_bytes))
            s_storage = int(ratio * 55)

        # 3. Penalties subtraction
        sum_penalties = sum(unresolved_penalties)
        
        score = (s_base + s_storage) - sum_penalties
        return min(100, max(0, score))

    @staticmethod
    def map_penalty_value(severity: str) -> int:
        """Maps risk severity levels to dynamic Readiness Score penalty points."""
        penalties = {
            "CRITICAL": 20,
            "HIGH": 10,
            "MEDIUM": 5,
            "LOW": 1
        }
        return penalties.get(severity, 0)
