"""
Phoenix Backup Recovery Recommendation Engine Module (Hardened Python Implementation)
"""

import logging
from typing import List, Dict, Any, Set, Optional
from shared.intelligence.models import RiskFinding, RecoveryAction, RecoverySequence
from shared.intelligence.classifier import UnknownAppClassifier

logger = logging.getLogger("phoenix.intelligence.recommendation")


class RecoveryRecommendationEngine:
    """
    Engine responsible for converting risk findings and app inventories into prioritized,
    topologically sorted recovery actions, detecting blockers, and generating the final recovery sequence.
    """

    def __init__(self, classifier: Optional[UnknownAppClassifier] = None):
        self.classifier = classifier or UnknownAppClassifier()

    def generate_sequence(
        self,
        findings: List[RiskFinding],
        app_inventory: List[Dict[str, Any]],
        device_info: Dict[str, Any]
    ) -> RecoverySequence:
        """
        Builds, resolves, and sorts the recovery actions sequence.
        """
        logger.info("Generating recovery sequence for %d apps and %d findings...", len(app_inventory), len(findings))

        # 1. Resolve Categories for Inventory Apps
        apps_with_categories: List[Dict[str, Any]] = []
        for app in app_inventory:
            pkg = app["package_name"]
            app_name = app["app_name"]
            
            # Find category
            # Standardize checking rule/category
            cat = app.get("category")
            if not cat:
                # Use classifier heuristic/rules fallback
                # Pass mocked empty permissions/metadata to classify category
                res = self.classifier.classify_app(
                    package_name=pkg,
                    app_name=app_name,
                    permissions=[],
                    metadata={"allow_backup": app.get("allow_backup", True), "is_system": app.get("is_system", False)}
                )
                cat = res.category
            
            apps_with_categories.append({
                "package_name": pkg,
                "app_name": app_name,
                "category": cat,
                "is_system": bool(app.get("is_system", False)),
                "allow_backup": bool(app.get("allow_backup", True))
            })

        # Separate apps by category for dependency linking
        auth_action_ids: List[str] = []
        pw_action_ids: List[str] = []

        actions_map: Dict[str, RecoveryAction] = {}
        findings_map = {f.package_name: f for f in findings}

        # 2. Generate Core Prerequisite Actions
        # SIM Activation
        is_tablet = "tablet" in (device_info.get("model") or "").lower() or bool(device_info.get("is_tablet", False))
        sim_priority = "LOW" if is_tablet else "CRITICAL"
        sim_desc = (
            "Tablet profile detected. SIM verification is typically optional unless utilizing cellular data bindings."
            if is_tablet else
            "Ensure the active SIM card registered for MFA/UPI is inserted into the target device and is receiving SMS messages."
        )
        sim_action = RecoveryAction(
            action_id="verify_sim",
            title="Verify Cellular SIM Serial and SMS Connectivity",
            description=sim_desc,
            category="PREREQUISITE",
            priority=sim_priority,
            depends_on=[],
            status="READY"
        )
        actions_map[sim_action.action_id] = sim_action

        # Google Account
        google_action = RecoveryAction(
            action_id="verify_google_account",
            title="Verify Primary Identity Account Credentials",
            description="Confirm login password for your primary Google account, ensuring you can log in on the new device to sync contacts and install apps.",
            category="IDENTITY",
            priority="CRITICAL",
            depends_on=[],
            status="READY"
        )
        actions_map[google_action.action_id] = google_action

        # 3. Create App-Specific Actions
        for app in apps_with_categories:
            pkg = app["package_name"]
            app_name = app["app_name"]
            cat = app["category"]
            
            action_id = f"restore_app_{pkg}"
            
            # Map category details
            priority = "MEDIUM"
            base_desc = f"Install {app_name} from the app store and log in."
            
            if cat == "AUTHENTICATOR":
                priority = "CRITICAL"
                base_desc = f"Restore {app_name} MFA tokens. Aegis: restore local vault. Google: scan export QR. Microsoft: enable cloud sync."
                auth_action_ids.append(action_id)
            elif cat == "PASSWORD_MANAGER":
                priority = "HIGH"
                base_desc = f"Restore {app_name} vault. Confirm master password and sync local/cloud backups."
                pw_action_ids.append(action_id)
            elif cat == "EMAIL":
                priority = "HIGH"
                base_desc = f"Set up email account in {app_name}. Verify server configurations and sync active mails."
            elif cat == "SECURE_MESSENGER":
                priority = "HIGH"
                base_desc = f"Restore {app_name} chat history. Signal: write 30-digit key and move backup files. WhatsApp: sync from cloud."
            elif cat in ("BANKING", "UPI"):
                priority = "HIGH"
                base_desc = f"Register {app_name} payment profile. Requires SMS capability and credential verifications."
            elif cat == "CLOUD_STORAGE":
                priority = "MEDIUM"
                base_desc = f"Sync cloud storage folders for {app_name}. Confirm all uploads finished before reset."
            elif cat == "NOTE_TAKING":
                priority = "MEDIUM"
                base_desc = f"Sync {app_name} note books. Verify local folder structure is backed up."
            elif cat == "GALLERY":
                priority = "MEDIUM"
                base_desc = f"Sync local photos/videos for {app_name}. Move remaining files to backup media."
            elif cat in ("VPN", "PRODUCTIVITY", "SOCIAL_MEDIA"):
                priority = "LOW"
                base_desc = f"Verify synchronization for {app_name} is complete."

            # Incorporate finding remediation if available
            finding = findings_map.get(pkg)
            status = "READY"
            if finding:
                status = "COMPLETED" if finding.resolved else "PENDING"
                if finding.remediation:
                    base_desc += f" Remediation requirement: {finding.remediation}"

            actions_map[action_id] = RecoveryAction(
                action_id=action_id,
                title=f"Restore {app_name}",
                description=base_desc,
                category=cat,
                priority=priority,
                depends_on=[], # resolved in next step
                status=status,
                associated_package=pkg
            )

        # 4. Populate App Dependencies
        for action_id, action in actions_map.items():
            if action_id in ("verify_sim", "verify_google_account"):
                continue
            
            cat = action.category
            
            if cat == "AUTHENTICATOR":
                action.depends_on = ["verify_google_account"]
            elif cat == "PASSWORD_MANAGER":
                action.depends_on = list(auth_action_ids) if auth_action_ids else ["verify_google_account"]
            elif cat == "EMAIL":
                action.depends_on = list(pw_action_ids) if pw_action_ids else ["verify_google_account"]
            elif cat == "SECURE_MESSENGER":
                action.depends_on = (list(auth_action_ids) if auth_action_ids else ["verify_google_account"]) + ["verify_sim"]
            elif cat in ("BANKING", "UPI", "FINANCIAL"):
                action.depends_on = (list(pw_action_ids) if pw_action_ids else ["verify_google_account"]) + ["verify_sim"]
            else:
                # General app categories
                action.depends_on = list(pw_action_ids) if pw_action_ids else ["verify_google_account"]

        # 5. Cascading Blocker Detection (DFS with Memoization)
        memo_blocked: Dict[str, bool] = {}
        memo_blockers_list: Dict[str, List[str]] = {}
        global_blockers: Set[str] = set()

        def evaluate_blockers(aid: str) -> tuple[bool, List[str]]:
            if aid in memo_blocked:
                return memo_blocked[aid], memo_blockers_list[aid]
            
            action = actions_map.get(aid)
            if not action:
                return False, []

            action_blockers = []
            
            # A node blocks downstream nodes if it is currently PENDING (unresolved risk)
            # Or if it's already BLOCKED
            is_blocked_node = False
            
            # Evaluate all dependencies
            for dep_id in action.depends_on:
                dep_action = actions_map.get(dep_id)
                if not dep_action:
                    continue
                
                # Check if dependency is directly PENDING (has unresolved risk finding)
                if dep_action.status == "PENDING":
                    is_blocked_node = True
                    desc = f"Blocked by '{dep_action.title}' (unresolved risk/pre-requisite)"
                    action_blockers.append(desc)
                    global_blockers.add(desc)
                
                # Check recursively if dependency is blocked
                dep_blocked, dep_blockers = evaluate_blockers(dep_id)
                if dep_blocked:
                    is_blocked_node = True
                    for db in dep_blockers:
                        desc = f"Indirectly blocked via dependency chain: {db}"
                        action_blockers.append(desc)
            
            if is_blocked_node:
                action.is_blocked = True
                action.status = "BLOCKED"
                action.blockers = list(set(action_blockers))

            memo_blocked[aid] = is_blocked_node
            memo_blockers_list[aid] = action.blockers
            return is_blocked_node, action.blockers

        # Evaluate blockers for all nodes
        for action_id in list(actions_map.keys()):
            evaluate_blockers(action_id)

        # 6. Topological Sorting (Kahn's Algorithm)
        # Build DAG representation
        # Adjacency list: node -> dependents
        adj: Dict[str, List[str]] = {aid: [] for aid in actions_map}
        in_degree: Dict[str, int] = {aid: 0 for aid in actions_map}

        for aid, action in actions_map.items():
            for dep in action.depends_on:
                if dep in adj:
                    adj[dep].append(aid)
                    in_degree[aid] += 1

        # Queue of nodes with in-degree = 0
        # To make sorting stable, sort them by category hierarchy and priority first
        # Category order value for sorting roots
        def get_sort_weight(aid: str) -> tuple[int, int, str]:
            action = actions_map[aid]
            cat_order = {
                "PREREQUISITE": 0,
                "IDENTITY": 1,
                "AUTHENTICATOR": 2,
                "PASSWORD_MANAGER": 3,
                "EMAIL": 4,
                "SECURE_MESSENGER": 5,
                "BANKING": 6,
                "UPI": 6,
                "FINANCIAL": 6,
                "CLOUD_STORAGE": 7,
                "NOTE_TAKING": 8,
                "GALLERY": 9,
                "VPN": 10,
                "PRODUCTIVITY": 11,
                "SOCIAL_MEDIA": 12,
                "UNKNOWN_APP": 13
            }
            priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            
            c_weight = cat_order.get(action.category, 99)
            p_weight = priority_order.get(action.priority, 9)
            return c_weight, p_weight, action.title

        # Process nodes
        sorted_ids = []
        zero_in_degree = [aid for aid in actions_map if in_degree[aid] == 0]
        
        while zero_in_degree:
            # Sort the queue to ensure stable/meaningful sequence order
            zero_in_degree.sort(key=get_sort_weight)
            curr = zero_in_degree.pop(0)
            sorted_ids.append(curr)
            
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    zero_in_degree.append(neighbor)

        # Cycle detection check
        if len(sorted_ids) < len(actions_map):
            logger.warning("Dependency cycle detected! Falling back to hierarchy sort.")
            # Fallback to sorting all actions directly by hierarchy weights
            sorted_ids = sorted(list(actions_map.keys()), key=get_sort_weight)

        sorted_actions = [actions_map[aid] for aid in sorted_ids]

        return RecoverySequence(
            actions=sorted_actions,
            blockers_detected=sorted(list(global_blockers))
        )
