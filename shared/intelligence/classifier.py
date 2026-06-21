"""
Phoenix Backup Unknown Application Classification Engine (Hardened Python Implementation)
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger("phoenix.intelligence.classifier")

@dataclass
class ClassificationResult:
    """Represents the output of the Unknown App Classification Engine."""
    category: str
    confidence_score: float
    risk_score: int
    recovery_complexity: str
    explanations: List[str] = field(default_factory=list)


# Classifiers parameters definition for 12 app categories
CLASSIFICATION_RULES: Dict[str, Dict[str, Any]] = {
    "AUTHENTICATOR": {
        "keywords": ["auth", "token", "2fa", "otp", "authenticator", "mfa", "aegis"],
        "weights": {"package": 40, "name": 30},
        "expected_permissions": [
            "android.permission.CAMERA",
            "android.permission.USE_BIOMETRIC",
            "android.permission.USE_FINGERPRINT"
        ],
        "base_risk": 90,
        "complexity": "CRITICAL",
        "reasoning": "TOTP credentials utilize local keystore binds. Extraction is strictly prevented."
    },
    "BANKING": {
        "keywords": ["bank", "pay", "wallet", "finance", "chase", "icici", "bofa", "hsbc", "credit", "card", "barclays"],
        "weights": {"package": 40, "name": 30},
        "expected_permissions": [
            "android.permission.INTERNET",
            "android.permission.READ_PHONE_STATE",
            "android.permission.USE_BIOMETRIC"
        ],
        "base_risk": 85,
        "complexity": "HIGH",
        "reasoning": "Banking portals use device-pin authentication keys and hardware bindings."
    },
    "UPI": {
        "keywords": ["upi", "paisa", "paytm", "phonepe", "bhim", "gpay"],
        "weights": {"package": 40, "name": 30},
        "expected_permissions": [
            "android.permission.SEND_SMS",
            "android.permission.RECEIVE_SMS",
            "android.permission.READ_PHONE_STATE"
        ],
        "base_risk": 85,
        "complexity": "HIGH",
        "reasoning": "UPI accounts bind to cellular SIM ICCID registers and mobile link networks."
    },
    "SECURE_MESSENGER": {
        "keywords": ["signal", "whatsapp", "messenger", "chat", "message", "telegram", "im", "securesms"],
        "weights": {"package": 35, "name": 25},
        "expected_permissions": [
            "android.permission.READ_CONTACTS",
            "android.permission.RECEIVE_SMS",
            "android.permission.RECORD_AUDIO",
            "android.permission.CAMERA"
        ],
        "base_risk": 90,
        "complexity": "CRITICAL",
        "reasoning": "Secure messengers maintain localized databases and disable standard backups."
    },
    "SOCIAL_MEDIA": {
        "keywords": ["instagram", "facebook", "twitter", "tiktok", "social", "snapchat", "reddit", "weibo"],
        "weights": {"package": 40, "name": 30},
        "expected_permissions": [
            "android.permission.INTERNET",
            "android.permission.CAMERA",
            "android.permission.RECORD_AUDIO"
        ],
        "base_risk": 50,
        "complexity": "MEDIUM",
        "reasoning": "Social profiles live in the cloud, but offline drafts are unrecoverable."
    },
    "EMAIL": {
        "keywords": ["email", "mail", "gmail", "outlook", "exchange", "imap", "pop3"],
        "weights": {"package": 40, "name": 30},
        "expected_permissions": [
            "android.permission.GET_ACCOUNTS",
            "android.permission.READ_CONTACTS",
            "android.permission.INTERNET"
        ],
        "base_risk": 30,
        "complexity": "LOW",
        "reasoning": "Mailboxes reside on cloud IMAP/Exchange database servers."
    },
    "PASSWORD_MANAGER": {
        "keywords": ["password", "vault", "bitwarden", "1password", "keepass", "roboform", "dashlane", "keychain"],
        "weights": {"package": 40, "name": 30},
        "expected_permissions": [
            "android.permission.USE_BIOMETRIC",
            "android.permission.INTERNET",
            "android.permission.AUTOFILL"
        ],
        "base_risk": 80,
        "complexity": "HIGH",
        "reasoning": "Encrypted credential vaults require master key files and sync configurations."
    },
    "CLOUD_STORAGE": {
        "keywords": ["drive", "dropbox", "onedrive", "cloud", "storage", "backup", "box", "sync"],
        "weights": {"package": 35, "name": 25},
        "expected_permissions": [
            "android.permission.INTERNET",
            "android.permission.READ_EXTERNAL_STORAGE",
            "android.permission.WRITE_EXTERNAL_STORAGE"
        ],
        "base_risk": 20,
        "complexity": "LOW",
        "reasoning": "Cloud file shares sync to servers. Verify pending uploads."
    },
    "NOTE_TAKING": {
        "keywords": ["note", "keep", "obsidian", "onenote", "editor", "todo", "notebook", "notes"],
        "weights": {"package": 35, "name": 25},
        "expected_permissions": [
            "android.permission.INTERNET",
            "android.permission.READ_EXTERNAL_STORAGE"
        ],
        "base_risk": 40,
        "complexity": "MEDIUM",
        "reasoning": "Local note directories require manual copy; cloud notes sync automatically."
    },
    "GALLERY": {
        "keywords": ["gallery", "photo", "picture", "image", "video", "media", "photos", "album"],
        "weights": {"package": 35, "name": 25},
        "expected_permissions": [
            "android.permission.READ_EXTERNAL_STORAGE",
            "android.permission.WRITE_EXTERNAL_STORAGE",
            "android.permission.READ_MEDIA_IMAGES"
        ],
        "base_risk": 50,
        "complexity": "MEDIUM",
        "reasoning": "Local media directories (DCIM/Pictures) will be deleted on reset."
    },
    "VPN": {
        "keywords": ["vpn", "expressvpn", "nordvpn", "proxy", "tunnel", "wireguard", "openvpn"],
        "weights": {"package": 40, "name": 30},
        "expected_permissions": [
            "android.permission.BIND_VPN_SERVICE",
            "android.permission.INTERNET"
        ],
        "base_risk": 25,
        "complexity": "LOW",
        "reasoning": "VPN profile settings sync from servers. Locate authentication codes."
    },
    "PRODUCTIVITY": {
        "keywords": ["slack", "teams", "trello", "zoom", "calendar", "meeting", "asana", "jira", "notion"],
        "weights": {"package": 35, "name": 25},
        "expected_permissions": [
            "android.permission.INTERNET",
            "android.permission.READ_CALENDAR"
        ],
        "base_risk": 30,
        "complexity": "LOW",
        "reasoning": "Productivity boards and workplace histories reside on enterprise cloud servers."
    }
}


class UnknownAppClassifier:
    """
    Engine responsible for classifying unknown Android apps, calculating confidence
    and risk metrics using rule-based algorithms.
    """

    def __init__(self, custom_rules: Optional[Dict[str, Dict[str, Any]]] = None):
        self.rules = custom_rules or CLASSIFICATION_RULES

    def classify_app(
        self,
        package_name: str,
        app_name: str,
        permissions: List[str],
        metadata: Dict[str, Any]
    ) -> ClassificationResult:
        """
        Runs the rule-based classification voting loop.
        """
        logger.info("Classifying unknown app: %s (%s)", app_name, package_name)
        
        votes: Dict[str, int] = {}
        explanations: List[str] = []
        
        package_lower = package_name.lower()
        app_lower = app_name.lower()
        permissions_set = set(permissions)
        
        import re
        package_tokens = re.split(r'[\._\-]', package_lower)
        app_tokens = re.split(r'[\s\._\-]', app_lower)

        # 1. Calculate matching score for each category
        for category, config in self.rules.items():
            score = 0
            category_explanations = []

            # Keyword matches
            for keyword in config["keywords"]:
                package_matched = False
                for token in package_tokens:
                    if len(keyword) <= 3:
                        if token == keyword or token.startswith(keyword):
                            package_matched = True
                            break
                    else:
                        if keyword in token:
                            package_matched = True
                            break
                if package_matched:
                    score += config["weights"]["package"]
                    category_explanations.append(f"Package segment matches keyword '{keyword}' (+{config['weights']['package']}pts)")

                app_matched = False
                for token in app_tokens:
                    if len(keyword) <= 3:
                        if token == keyword or token.startswith(keyword):
                            app_matched = True
                            break
                    else:
                        if keyword in token:
                            app_matched = True
                            break
                if app_matched:
                    score += config["weights"]["name"]
                    category_explanations.append(f"App label matches keyword '{keyword}' (+{config['weights']['name']}pts)")

            # Permissions support matches
            for perm in config["expected_permissions"]:
                if perm in permissions_set:
                    score += 12
                    category_explanations.append(f"Requests target permission '{perm.split('.')[-1]}' (+12pts)")

            if score > 0:
                votes[category] = score
                # Store candidate explanations
                logger.debug("Candidate %s scored %d", category, score)

        # 2. Select winner or fallback
        if not votes:
            explanations.append("No keywords or permissions matched. Falling back to UNKNOWN_APP default profile.")
            category = "UNKNOWN_APP"
            confidence = 0.50
            base_risk = 30
            complexity = "LOW"
        else:
            # Pick category with highest score
            category = max(votes, key=votes.get)
            top_score = votes[category]
            
            # Recalculate explanations for the winner
            explanations.append(f"Classified as {category} based on matching score of {top_score}.")
            
            # Recalculate context for explanation details
            config = self.rules[category]
            for keyword in config["keywords"]:
                package_matched = False
                for token in package_tokens:
                    if len(keyword) <= 3:
                        if token == keyword or token.startswith(keyword):
                            package_matched = True
                            break
                    else:
                        if keyword in token:
                            package_matched = True
                            break
                if package_matched:
                    explanations.append(f"Package segment matches keyword '{keyword}' (+{config['weights']['package']}pts)")

                app_matched = False
                for token in app_tokens:
                    if len(keyword) <= 3:
                        if token == keyword or token.startswith(keyword):
                            app_matched = True
                            break
                    else:
                        if keyword in token:
                            app_matched = True
                            break
                if app_matched:
                    explanations.append(f"App label matches keyword '{keyword}' (+{config['weights']['name']}pts)")
            
            for perm in config["expected_permissions"]:
                if perm in permissions_set:
                    explanations.append(f"Requests target permission '{perm.split('.')[-1]}' (+12pts)")

            # 3. Calculate Confidence Score
            # Exact matches get high confidence, heuristics scaled by score
            confidence = min(0.95, 0.65 + (top_score / 150.0))
            base_risk = config["base_risk"]
            complexity = config["complexity"]

        # 4. Integrate APK Metadata into risk calculations
        allow_backup = bool(metadata.get("allow_backup", True))
        is_system = bool(metadata.get("is_system", False))
        api_level = int(metadata.get("api_level", 30))

        # Risk Adjustments
        risk_score = base_risk
        if not allow_backup:
            risk_score += 15
            explanations.append("App explicitly disables allowBackup flag (+15 risk penalty).")
        if is_system:
            risk_score -= 20
            explanations.append("App registered in system partition (-20 risk discount).")
        if api_level >= 31 and not is_system and category != "UNKNOWN_APP":
            # Extra risk on API 31+ due to default ADB blockages
            risk_score += 5
            explanations.append("Device is Android 12+ (API >= 31) user app, complicating extraction.")

        # Clamp risk score
        risk_score = max(0, min(100, risk_score))

        # Complexity Adjustments
        if not allow_backup:
            if complexity in ("MEDIUM", "LOW"):
                complexity = "HIGH"
                explanations.append("Complexity escalated to HIGH due to allowBackup=false status.")

        return ClassificationResult(
            category=category,
            confidence_score=round(confidence, 2),
            risk_score=risk_score,
            recovery_complexity=complexity,
            explanations=explanations
        )
