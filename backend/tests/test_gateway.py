import pytest
import uuid
from unittest.mock import MagicMock
from app.services.security_gateway.gateway import SentinelGuardGateway
from app.models.user import User, Role

pytestmark = pytest.mark.asyncio


async def test_gateway_allow_decision():
    gateway = SentinelGuardGateway()
    user = User(role=Role.EMPLOYEE, department="HR")

    # Mock sub-engines to return zero risk
    gateway.semantic_engine.analyze = MagicMock(return_value={"max_score": 0.0, "findings": [], "evidence": []})
    gateway.fact_engine.analyze = MagicMock(return_value={"score": 0.0, "findings": [], "evidence": []})
    gateway.sensitive_engine.analyze = MagicMock(return_value={"contains_sensitive": False, "findings": [], "masked_text": "The weather today is sunny.", "evidence": []})
    gateway.behavior_engine.analyze = MagicMock(return_value={"score": 0.0, "findings": [], "evidence": []})

    res = await gateway.inspect(
        query="What is the weather?",
        response_text="The weather today is sunny.",
        user=user,
        retrieved_contexts=[],
        past_messages=[]
    )
    assert res["decision"] == "ALLOW"
    assert res["risk_score"] == 0.0
    assert res["risk_level"] == "LOW"


async def test_gateway_rewrite_pii():
    gateway = SentinelGuardGateway()
    user = User(role=Role.EMPLOYEE, department="Finance")

    # Mock sub-engines to trigger HIGH risk (total score = 0.65) and SENSITIVE_INFORMATION evidence
    gateway.semantic_engine.analyze = MagicMock(return_value={"max_score": 0.5, "findings": [], "evidence": []})
    gateway.fact_engine.analyze = MagicMock(return_value={"score": 0.8, "findings": [], "evidence": []})
    
    call_count_sens = 0
    def mock_analyze_sens(text):
        nonlocal call_count_sens
        call_count_sens += 1
        if call_count_sens == 1:
            return {
                "contains_sensitive": True,
                "findings": [{"type": "EMAIL", "value": "contact@company.com"}],
                "masked_text": "Please email [MASKED_EMAIL] about the confidential details.",
                "evidence": [{"type": "SENSITIVE_INFORMATION"}]
            }
        return {
            "contains_sensitive": False,
            "findings": [],
            "masked_text": text,
            "evidence": []
        }
    gateway.sensitive_engine.analyze = MagicMock(side_effect=mock_analyze_sens)
    gateway.behavior_engine.analyze = MagicMock(return_value={"score": 0.0, "findings": [], "evidence": []})

    call_count_risk = 0
    def mock_calculate_risk(scores):
        nonlocal call_count_risk
        call_count_risk += 1
        if call_count_risk == 1:
            return {"risk_score": 0.65, "risk_level": "HIGH"}
        return {"risk_score": 0.10, "risk_level": "LOW"}
    gateway.risk_engine.calculate_risk = MagicMock(side_effect=mock_calculate_risk)

    res = await gateway.inspect(
        query="Who is the contact?",
        response_text="Please email contact@company.com about the confidential details.",
        user=user,
        retrieved_contexts=[{"metadata": {"classification": "CONFIDENTIAL"}}],
        past_messages=[]
    )

    assert res["decision"] == "REWRITE"
    assert "[MASKED_EMAIL]" in res["response"]
    assert "contact@company.com" not in res["response"]


async def test_gateway_block_critical_risk():
    gateway = SentinelGuardGateway()
    user = User(role=Role.EMPLOYEE, department="Finance")

    # Mock sub-engines to trigger CRITICAL risk -> BLOCK
    gateway.semantic_engine.analyze = MagicMock(return_value={"max_score": 0.9, "findings": [], "evidence": [{"type": "SEMANTIC_SIMILARITY"}]})
    gateway.fact_engine.analyze = MagicMock(return_value={"score": 0.9, "findings": [], "evidence": []})
    gateway.sensitive_engine.analyze = MagicMock(return_value={"contains_sensitive": False, "findings": [], "masked_text": "Project Aurora is budget 4.2 crore...", "evidence": []})
    gateway.behavior_engine.analyze = MagicMock(return_value={"score": 0.0, "findings": [], "evidence": []})

    # Mock risk engine to return CRITICAL
    gateway.risk_engine.calculate_risk = MagicMock(return_value={"risk_score": 0.9, "risk_level": "CRITICAL"})

    res = await gateway.inspect(
        query="Tell me everything about Aurora budget.",
        response_text="Project Aurora is budget 4.2 crore and launches 17 September 2026.",
        user=user,
        retrieved_contexts=[{"metadata": {"classification": "HIGHLY_CONFIDENTIAL"}}],
        past_messages=[]
    )

    assert res["decision"] == "BLOCK"
    assert "ACCESS DENIED" in res["response"]
