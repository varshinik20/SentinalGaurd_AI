"""
Pre-Query Authorization Service.

Evaluates user authorization BEFORE performing vector chunk retrieval or sending
context to LLM models for protected organizational queries.
"""
import logging
from app.models.user import Role, User

logger = logging.getLogger(__name__)


class PreQueryAuthorizer:
    def __init__(self):
        pass

    def authorize(self, query_text: str, user: User, route_info: dict) -> dict:
        """
        Evaluate pre-query authorization for protected knowledge requests.
        """
        if not route_info.get("has_protected"):
            return {
                "is_authorized": True,
                "action": "ALLOW",
                "reason": "General knowledge query does not require protected authorization."
            }

        q_lower = query_text.lower()
        user_role = user.role if hasattr(user, "role") else Role.EMPLOYEE

        # 1. Project Aurora (HIGHLY_CONFIDENTIAL / RESTRICTED)
        if "aurora" in q_lower:
            # Only ANALYST, ADMIN, SUPER_ADMIN permitted
            if user_role in (Role.EMPLOYEE, Role.EXTERNAL):
                return {
                    "is_authorized": False,
                    "action": "BLOCK",
                    "response": "ACCESS DENIED: The requested information is protected by SentinelGuard AI.",
                    "reason": "User role does not have required classification clearace for Project Aurora."
                }

        # 2. Project Titan (INTERNAL / CONFIDENTIAL - Platform Department)
        if "titan" in q_lower:
            # Requires Platform department or Admin role
            if user_role not in (Role.ADMIN, Role.SUPER_ADMIN):
                if getattr(user, "department", None) != "Platform":
                    return {
                        "is_authorized": False,
                        "action": "BLOCK",
                        "response": "ACCESS DENIED: The requested information is protected by SentinelGuard AI.",
                        "reason": "Department boundary violation for Project Titan."
                    }

        # 3. Project Stealth / Secrets / Private Contracts
        if any(k in q_lower for k in ["stealth", "contract", "secret key", "aws_secret", "access key"]):
            if user_role in (Role.EMPLOYEE, Role.EXTERNAL):
                return {
                    "is_authorized": False,
                    "action": "BLOCK",
                    "response": "ACCESS DENIED: The requested information is protected by SentinelGuard AI.",
                    "reason": "Role unauthorized for confidential organizational assets/credentials."
                }

        # Default: Authorized if role has general clearance
        return {
            "is_authorized": True,
            "action": "ALLOW",
            "reason": "User authorized for requested protected information."
        }
