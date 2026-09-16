import pytest
import os
from app.services.security_gateway.policy import PolicyEngine


def test_policy_sequential_matching():
    # Load default policies from local policies.yaml
    engine = PolicyEngine()

    # 1. Critical risk matches first rule
    ctx1 = {"risk_level": "CRITICAL"}
    res1 = engine.evaluate(ctx1)
    assert res1["name"] == "BLOCK_CRITICAL_RISK"
    assert res1["action"] == "BLOCK"

    # 2. High risk with PII -> REWRITE
    ctx2 = {
        "risk_level": "HIGH",
        "evidence_types": ["SENSITIVE_INFORMATION"]
    }
    res2 = engine.evaluate(ctx2)
    assert res2["name"] == "REWRITE_HIGH_RISK_PII"
    assert res2["action"] == "REWRITE"

    # 3. External role trying to read CONFIDENTIAL -> BLOCK
    ctx3 = {
        "risk_level": "LOW",
        "user_role": "EXTERNAL",
        "max_classification": "CONFIDENTIAL"
    }
    res3 = engine.evaluate(ctx3)
    assert res3["name"] == "BLOCK_EXTERNAL_CONFIDENTIAL"
    assert res3["action"] == "BLOCK"

    # 4. Low risk clean context -> DEFAULT_ALLOW
    ctx4 = {
        "risk_level": "LOW",
        "user_role": "EMPLOYEE",
        "max_classification": "PUBLIC",
        "evidence_types": []
    }
    res4 = engine.evaluate(ctx4)
    assert res4["name"] == "DEFAULT_ALLOW"
    assert res4["action"] == "ALLOW"
