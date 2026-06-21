"""
Phoenix Backup Recovery Intelligence Data Models (Hardened Python Implementation)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class AppRuleDefinition:
    """Represents a static risk rule for a known application package pattern."""
    package_pattern: str
    app_name: str
    category: str
    severity: str
    reasoning: str
    remediation: str

@dataclass
class RiskFinding:
    """Represents a flagged risk finding on a user's scanned application."""
    package_name: str
    app_name: str
    category: str
    severity: str
    reasoning: str
    remediation: str
    resolved: bool = False

@dataclass
class ChecklistTask:
    """Represents an actionable manual step in the user recovery checklist."""
    task_id: str
    step: str
    priority: str  # MUST, SHOULD, COULD
    timing: str    # PRE_RESET, POST_RESTORE
    status: str    # PENDING, COMPLETED

@dataclass
class ReadinessAssessment:
    """Represents the compiled readiness report containing the score, checklists, and inventory."""
    readiness_score: int
    readiness_state: str  # READY, WARNING, CRITICAL_UNPREPARED
    verdicts: Dict[str, bool]  # {'contacts_ready': bool, 'sms_ready': bool, 'call_logs_ready': bool}
    overall_assessment: str
    findings: List[RiskFinding] = field(default_factory=list)
    checklist: List[ChecklistTask] = field(default_factory=list)
    inventory: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class RecoveryAction:
    """Represents a prioritized, sequence-sorted step in the recovery flow."""
    action_id: str
    title: str
    description: str
    category: str  # PREREQUISITE, IDENTITY, AUTHENTICATOR, PASSWORD_MANAGER, EMAIL, SECURE_MESSENGER, FINANCIAL, GENERAL_APP
    priority: str  # CRITICAL, HIGH, MEDIUM, LOW
    depends_on: List[str] = field(default_factory=list)
    is_blocked: bool = False
    blockers: List[str] = field(default_factory=list)
    status: str = "PENDING"  # PENDING, READY, BLOCKED, COMPLETED
    associated_package: Optional[str] = None

@dataclass
class RecoverySequence:
    """Represents the complete list of prioritized and topologically sorted recovery actions."""
    actions: List[RecoveryAction] = field(default_factory=list)
    blockers_detected: List[str] = field(default_factory=list)

@dataclass
class BackupComparisonReport:
    """Represents the output differential comparison between two execution jobs."""
    base_job_id: str
    target_job_id: str
    device_id: str
    base_readiness_score: int
    target_readiness_score: int
    readiness_score_delta: int
    readiness_improved: bool
    added_apps: List[Dict[str, Any]] = field(default_factory=list)
    removed_apps: List[Dict[str, Any]] = field(default_factory=list)
    new_risks: List[Dict[str, Any]] = field(default_factory=list)
    resolved_risks: List[Dict[str, Any]] = field(default_factory=list)
    inventory_size_delta: int = 0
