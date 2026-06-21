"""
Phoenix Backup Historical Backup Comparison Engine Module (Hardened Python Implementation)
"""

import logging
from typing import List, Dict, Any, Optional
from shared.db.connection import DatabaseConnectionManager
from shared.db.repositories import BackupJobRepository, JobAppInventoryRepository
from shared.intelligence.models import BackupComparisonReport

logger = logging.getLogger("phoenix.intelligence.comparison")


class BackupComparisonEngine:
    """
    Engine responsible for comparing two historical backup jobs,
    reporting changes in readiness scores, inventory additions/deletions, and risk profile shifts.
    """

    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager

    def compare_jobs(self, base_job_id: str, target_job_id: str) -> BackupComparisonReport:
        """
        Compares two historical backup executions.
        Raises ValueError if base_job_id or target_job_id does not exist,
        or if they belong to different devices.
        """
        logger.info("Comparing base job [%s] with target job [%s]...", base_job_id, target_job_id)

        with self.db_manager.get_connection(read_only=True) as conn:
            job_repo = BackupJobRepository(conn)
            job_app_repo = JobAppInventoryRepository(conn)

            # 1. Fetch Job Metadata
            base_job = job_repo.get_job(base_job_id)
            if not base_job:
                raise ValueError(f"Base job ID '{base_job_id}' not found in database.")

            target_job = job_repo.get_job(target_job_id)
            if not target_job:
                raise ValueError(f"Target job ID '{target_job_id}' not found in database.")

            # Validate same device
            base_device = base_job["device_id"]
            target_device = target_job["device_id"]
            if base_device != target_device:
                raise ValueError(
                    f"Cannot compare jobs across different devices: "
                    f"Base device='{base_device}', Target device='{target_device}'"
                )

            # Extract scores (default to 0 if not completed/null)
            base_score = base_job.get("readiness_score") or 0
            target_score = target_job.get("readiness_score") or 0

            # 2. Fetch Job App Inventories
            base_apps_list = job_app_repo.get_apps_for_job(base_job_id)
            target_apps_list = job_app_repo.get_apps_for_job(target_job_id)

        # Map inventories by package name
        base_apps = {app["package_name"]: app for app in base_apps_list}
        target_apps = {app["package_name"]: app for app in target_apps_list}

        base_pkgs = set(base_apps.keys())
        target_pkgs = set(target_apps.keys())

        # 3. App Additions & Deletions
        added_pkgs = target_pkgs - base_pkgs
        removed_pkgs = base_pkgs - target_pkgs

        added_apps = [
            {
                "package_name": pkg,
                "app_name": target_apps[pkg]["app_name"],
                "category": target_apps[pkg]["category"],
                "risk_score": target_apps[pkg]["risk_score"]
            }
            for pkg in added_pkgs
        ]

        removed_apps = [
            {
                "package_name": pkg,
                "app_name": base_apps[pkg]["app_name"],
                "category": base_apps[pkg]["category"],
                "risk_score": base_apps[pkg]["risk_score"]
            }
            for pkg in removed_pkgs
        ]

        # Sort lists by package name for stable outputs
        added_apps.sort(key=lambda x: x["package_name"])
        removed_apps.sort(key=lambda x: x["package_name"])

        # 4. New & Resolved Risks Calculations
        new_risks = []
        resolved_risks = []

        # Analyze Added Apps for High Risks (risk >= 50)
        for app in added_apps:
            if app["risk_score"] >= 50:
                new_risks.append({
                    "package_name": app["package_name"],
                    "app_name": app["app_name"],
                    "category": app["category"],
                    "base_risk": 0,
                    "target_risk": app["risk_score"],
                    "reason": "New application installed with high risk profile."
                })

        # Analyze Removed Apps for resolved risks
        for app in removed_apps:
            if app["risk_score"] >= 50:
                resolved_risks.append({
                    "package_name": app["package_name"],
                    "app_name": app["app_name"],
                    "category": app["category"],
                    "base_risk": app["risk_score"],
                    "target_risk": 0,
                    "reason": "High risk application uninstalled."
                })

        # Analyze Common Apps for risk differentials & override toggles
        common_pkgs = base_pkgs & target_pkgs
        for pkg in common_pkgs:
            base_app = base_apps[pkg]
            target_app = target_apps[pkg]

            base_risk = base_app["risk_score"]
            target_risk = target_app["risk_score"]
            
            base_resolved = bool(base_app["resolved"])
            target_resolved = bool(target_app["resolved"])

            # Flag risk escalation
            is_escalated = target_risk > base_risk
            is_unresolved = base_resolved and not target_resolved

            if is_escalated or is_unresolved:
                reason = "Risk score escalated." if is_escalated else "User override resolved status was revoked."
                new_risks.append({
                    "package_name": pkg,
                    "app_name": target_app["app_name"],
                    "category": target_app["category"],
                    "base_risk": base_risk,
                    "target_risk": target_risk,
                    "reason": reason
                })

            # Flag risk reduction/resolution
            is_reduced = target_risk < base_risk
            is_newly_resolved = not base_resolved and target_resolved

            if is_reduced or is_newly_resolved:
                reason = "Risk score reduced." if is_reduced else "User override applied, resolving finding."
                resolved_risks.append({
                    "package_name": pkg,
                    "app_name": target_app["app_name"],
                    "category": target_app["category"],
                    "base_risk": base_risk,
                    "target_risk": target_risk,
                    "reason": reason
                })

        # Sort risks lists by package name for stable outputs
        new_risks.sort(key=lambda x: x["package_name"])
        resolved_risks.sort(key=lambda x: x["package_name"])

        # 5. Compile Differential Report
        score_delta = target_score - base_score
        improved = score_delta > 0
        inventory_delta = len(target_pkgs) - len(base_pkgs)

        return BackupComparisonReport(
            base_job_id=base_job_id,
            target_job_id=target_job_id,
            device_id=base_device,
            base_readiness_score=base_score,
            target_readiness_score=target_score,
            readiness_score_delta=score_delta,
            readiness_improved=improved,
            added_apps=added_apps,
            removed_apps=removed_apps,
            new_risks=new_risks,
            resolved_risks=resolved_risks,
            inventory_size_delta=inventory_delta
        )
