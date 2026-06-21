"""
Phoenix Backup Findings Engine Module (Hardened Python Implementation)
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from shared.intelligence.models import RiskFinding, ChecklistTask
from shared.intelligence.rules import ApplicationClassifier
from shared.intelligence.scoring import RiskScoreCalculator, RecoveryReadinessCalculator

logger = logging.getLogger("phoenix.intelligence.findings")

class FindingsEngine:
    """
    Engine responsible for converting raw application metadata and risk scores
    into human-readable risk findings and recovery checklist tasks.
    """

    def __init__(self, classifier: ApplicationClassifier, unknown_classifier: Optional[Any] = None):
        self.classifier = classifier
        self.unknown_classifier = unknown_classifier

    def compile_findings_and_checklist(
        self,
        db_apps: List[Dict[str, Any]],
        user_overrides: List[str]
    ) -> Tuple[List[RiskFinding], List[ChecklistTask], List[int]]:
        """
        Processes scanned applications, matches them against rules, computes risk levels,
        and generates explainable findings, checklist items, and active penalties.
        """
        logger.info("Compiling recovery findings and checklist items for %d apps...", len(db_apps))
        findings: List[RiskFinding] = []
        checklist: List[ChecklistTask] = []
        unresolved_penalties: List[int] = []

        for app in db_apps:
            package_name = app["package_name"]
            app_name = app["app_name"]
            is_system = bool(app["is_system"])
            allow_backup = bool(app["allow_backup"])

            rule = self.classifier.match_rule(package_name)
            category = "Unknown"
            severity = "LOW"
            reasoning = "Unrecognized application. Standard backup policy applies."
            remediation = "Confirm you can log in on your target device."

            if rule:
                category = rule.category
                severity = rule.severity
                reasoning = rule.reasoning
                remediation = rule.remediation
            else:
                if self.unknown_classifier:
                    permissions = app.get("permissions") or []
                    metadata = {
                        "allow_backup": allow_backup,
                        "is_system": is_system,
                        "api_level": app.get("api_level") or 30
                    }
                    res = self.unknown_classifier.classify_app(package_name, app_name, permissions, metadata)
                    category = res.category
                    
                    # Fetch reasoning and remediation from rules config
                    rule_config = self.unknown_classifier.rules.get(category)
                    if rule_config:
                        reasoning = rule_config["reasoning"]
                        remediation_map = {
                            "AUTHENTICATOR": "Manually export accounts via QR code if supported.",
                            "BANKING": "Ensure you know login passwords and have an active SMS SIM line.",
                            "UPI": "Ensure you know login passwords and have an active SMS SIM line.",
                            "SECURE_MESSENGER": "Export local database/chats or enable cloud backup.",
                            "PASSWORD_MANAGER": "Confirm master password and export vault backup file.",
                            "EMAIL": "Confirm credentials and server sync settings.",
                            "CLOUD_STORAGE": "Verify sync is complete before device reset.",
                            "NOTE_TAKING": "Copy local note folders to external storage.",
                            "GALLERY": "Copy all photos/videos to PC or cloud backup.",
                            "VPN": "Save profile config details.",
                            "PRODUCTIVITY": "Ensure cloud account sync is complete.",
                            "SOCIAL_MEDIA": "Sync drafts and verify credentials."
                        }
                        remediation = remediation_map.get(category, "Confirm you can log in on your target device.")
                    else:
                        category = "Unknown"
                else:
                    if any(t in package_name.lower() for t in ["auth", "token", "2fa", "otp"]):
                        category = "AUTHENTICATOR"
                        severity = "CRITICAL"
                        reasoning = "Potential authenticator/OTP application. Bound to Keystore keys."
                        remediation = "Manually export accounts via QR code if supported."
                    elif any(t in package_name.lower() for t in ["bank", "pay", "wallet", "finance"]):
                        category = "BANKING"
                        severity = "HIGH"
                        reasoning = "Financial portal. Hardware token bindings will trigger authentication lockouts."
                        remediation = "Ensure you know login passwords and have an active SMS SIM line."

            app_risk_score = RiskScoreCalculator.calculate_app_risk_score(
                category=category,
                allow_backup=allow_backup,
                is_system=is_system
            )
            computed_severity = RiskScoreCalculator.derive_risk_level(app_risk_score)
            if app_risk_score >= 70:
                severity = computed_severity

            # Compile into findings if risk is above low
            if severity in ("CRITICAL", "HIGH", "MEDIUM"):
                resolved = package_name in user_overrides
                finding = RiskFinding(
                    package_name=package_name,
                    app_name=app_name,
                    category=category,
                    severity=severity,
                    reasoning=reasoning,
                    remediation=remediation,
                    resolved=resolved
                )
                findings.append(finding)

                if not resolved:
                    penalty = RecoveryReadinessCalculator.map_penalty_value(severity)
                    unresolved_penalties.append(penalty)

                # Prioritize checklist task
                priority = "MUST" if severity == "CRITICAL" else ("SHOULD" if severity == "HIGH" else "COULD")
                checklist.append(
                    ChecklistTask(
                        task_id=f"task_{package_name}",
                        step=remediation,
                        priority=priority,
                        timing="PRE_RESET",
                        status="COMPLETED" if resolved else "PENDING"
                    )
                )

        return findings, checklist, unresolved_penalties

    def generate_remediation_summary(self, findings: List[RiskFinding]) -> Dict[str, Any]:
        """
        Summarizes findings to support future HTML and PDF template generation.
        """
        unresolved = [f for f in findings if not f.resolved]
        resolved = [f for f in findings if f.resolved]

        return {
            "total_risks_count": len(findings),
            "unresolved_risks_count": len(unresolved),
            "resolved_risks_count": len(resolved),
            "critical_unresolved_count": len([f for f in unresolved if f.severity == "CRITICAL"]),
            "high_unresolved_count": len([f for f in unresolved if f.severity == "HIGH"]),
            "medium_unresolved_count": len([f for f in unresolved if f.severity == "MEDIUM"])
        }
