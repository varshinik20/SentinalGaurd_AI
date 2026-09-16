"""
Policy Engine.

Loads sequential security rules from YAML and evaluates them against the
user role, department, classification levels, and hybrid risk metrics.
"""
import os
import yaml
from pathlib import Path


class PolicyEngine:
    # Classification order mapping
    CLASSIFICATION_ORDER = {
        "PUBLIC": 0,
        "INTERNAL": 1,
        "CONFIDENTIAL": 2,
        "HIGHLY_CONFIDENTIAL": 3,
        "RESTRICTED": 4
    }

    def __init__(self, policy_path: str | None = None):
        if policy_path is None:
            # Path to policies.yaml in backend/app/core/
            policy_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "core",
                "policies.yaml"
            )
        
        self.policy_path = policy_path
        self.policies = []
        self.load_policies()

    def load_policies(self) -> None:
        """Load YAML policy configurations."""
        if os.path.exists(self.policy_path):
            with open(self.policy_path, "r", encoding="utf-8") as f:
                try:
                    data = yaml.safe_load(f)
                    self.policies = data.get("policies", [])
                except Exception:
                    self.policies = []
        else:
            # Fallback inline default rules if file is missing
            self.policies = [
                {
                    "name": "BLOCK_CRITICAL_RISK",
                    "conditions": {"risk_level": "CRITICAL"},
                    "action": "BLOCK",
                    "description": "Block Critical risk levels."
                },
                {
                    "name": "DEFAULT_ALLOW",
                    "conditions": {},
                    "action": "ALLOW",
                    "description": "Allow by default."
                }
            ]

    def evaluate(self, context: dict) -> dict:
        """
        Evaluate sequential rules against a context map:
        - "risk_level": str ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        - "user_role": str ("EMPLOYEE", "ADMIN", "EXTERNAL", etc.)
        - "user_department": str
        - "max_classification": str ("PUBLIC", "CONFIDENTIAL", etc.)
        - "evidence_types": list[str] (["SENSITIVE_INFORMATION", ...])
        """
        for policy in self.policies:
            conditions = policy.get("conditions", {})
            if not conditions:
                # Default policy matches everything
                return {
                    "name": policy["name"],
                    "action": policy["action"],
                    "description": policy.get("description", "")
                }

            match = True
            for key, val in conditions.items():
                if key == "risk_level":
                    if context.get("risk_level") != val:
                        match = False
                        break
                elif key == "user_role":
                    if context.get("user_role") != val:
                        match = False
                        break
                elif key == "user_department":
                    if context.get("user_department") != val:
                        match = False
                        break
                elif key == "max_classification":
                    ctx_val = context.get("max_classification", "PUBLIC")
                    ctx_num = self.CLASSIFICATION_ORDER.get(ctx_val, 0)
                    rule_num = self.CLASSIFICATION_ORDER.get(val, 0)
                    if ctx_num < rule_num:
                        match = False
                        break
                elif key == "has_evidence_type":
                    evidence_types = context.get("evidence_types", [])
                    if val not in evidence_types:
                        match = False
                        break

            if match:
                return {
                    "name": policy["name"],
                    "action": policy["action"],
                    "description": policy.get("description", "")
                }

        return {
            "name": "DEFAULT_ALLOW",
            "action": "ALLOW",
            "description": "Fallback allow rule."
        }
