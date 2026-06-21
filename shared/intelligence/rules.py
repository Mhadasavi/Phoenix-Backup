"""
Phoenix Backup Risk Knowledge Base Rules Loader and Classifier (Hardened Python Implementation)
"""

import json
import logging
import os
import re
from typing import List, Optional
from shared.intelligence.models import AppRuleDefinition

logger = logging.getLogger("phoenix.intelligence.rules")

class RiskKnowledgeBaseLoader:
    """
    Service responsible for loading risk and recommendation definitions from a local JSON database.
    """

    def __init__(self, rules_path: Optional[str] = None):
        if not rules_path:
            rules_path = os.path.join(os.path.dirname(__file__), "rules.json")
        self.rules_path = os.path.abspath(rules_path)
        self.rules: List[AppRuleDefinition] = []

    def load_rules(self) -> List[AppRuleDefinition]:
        """
        Loads rules from the JSON configuration. Enforces robust error handling.
        """
        logger.info("Loading Risk Knowledge Base definitions from %s...", self.rules_path)
        if not os.path.exists(self.rules_path):
            logger.error("Risk rules file not found: %s", self.rules_path)
            return []

        try:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.rules = []
            for item in data:
                # Support schema key variations: "package_pattern" or "package_name"
                pattern = item.get("package_pattern") or item.get("package_name")
                if not pattern or not item.get("app_name") or not item.get("category"):
                    logger.debug("Skipping malformed rule entry: %s", item)
                    continue

                rule = AppRuleDefinition(
                    package_pattern=pattern,
                    app_name=item["app_name"],
                    category=item["category"],
                    severity=item.get("severity", "MEDIUM"),
                    reasoning=item.get("reasoning", ""),
                    remediation=item.get("remediation", "")
                )
                self.rules.append(rule)
            
            logger.info("Successfully loaded %d rules from configuration.", len(self.rules))
            return self.rules
        except (json.JSONDecodeError, KeyError, IOError) as err:
            logger.error("Failed to parse Risk Knowledge Base: %s", err)
            return []


class ApplicationClassifier:
    """
    Evaluates package names, classifications, and match heuristics.
    """

    def __init__(self, rules: List[AppRuleDefinition]):
        self.rules = rules

    def match_rule(self, package_name: str) -> Optional[AppRuleDefinition]:
        """
        Searches the rule definitions to find a match for a package name.
        Supports exact matches and glob-style package pattern resolution.
        """
        for rule in self.rules:
            pattern = rule.package_pattern
            # Simple wildcard conversion (e.g. "com.chase.*" -> "^com\.chase\..*")
            if "*" in pattern:
                regex_pattern = "^" + re.escape(pattern).replace(r"\*", ".*") + "$"
                if re.match(regex_pattern, package_name):
                    return rule
            elif pattern == package_name:
                return rule
                
        return None
