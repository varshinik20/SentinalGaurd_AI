import pytest
from app.services.security_gateway.hybrid_risk import HybridRiskEngine


def test_hybrid_risk_engine_weight_validation():
    # Sum of weights != 1.0 -> should raise ValueError
    invalid_weights = {
        "semantic_similarity": 0.5,
        "fact_leakage": 0.5,
        "sensitive_info": 0.5,
        "behavior": 0.5
    }
    with pytest.raises(ValueError):
        HybridRiskEngine(weights=invalid_weights)


def test_hybrid_risk_calculations():
    engine = HybridRiskEngine()

    # 1. All zero -> LOW
    scores_low = {
        "semantic_similarity": 0.0,
        "fact_leakage": 0.0,
        "sensitive_info": 0.0,
        "behavior": 0.0
    }
    res_low = engine.calculate_risk(scores_low)
    assert res_low["risk_score"] == 0.0
    assert res_low["risk_level"] == "LOW"

    # 2. Medium leak -> MEDIUM
    scores_med = {
        "semantic_similarity": 0.4,
        "fact_leakage": 0.3,
        "sensitive_info": 0.0,
        "behavior": 0.0
    }
    res_med = engine.calculate_risk(scores_med)
    # 0.4 * 0.35 + 0.3 * 0.35 = 0.14 + 0.105 = 0.245
    assert abs(res_med["risk_score"] - 0.245) < 0.001
    assert res_med["risk_level"] == "MEDIUM"

    # 3. High leak -> HIGH
    scores_high = {
        "semantic_similarity": 0.8,
        "fact_leakage": 0.8,
        "sensitive_info": 0.0,
        "behavior": 0.3
    }
    res_high = engine.calculate_risk(scores_high)
    # 0.8 * 0.35 + 0.8 * 0.35 + 0.0 * 0.20 + 0.3 * 0.10 = 0.28 + 0.28 + 0.03 = 0.59
    assert abs(res_high["risk_score"] - 0.59) < 0.001
    assert res_high["risk_level"] == "HIGH"

    # 4. Critical leak -> CRITICAL
    scores_crit = {
        "semantic_similarity": 0.9,
        "fact_leakage": 0.9,
        "sensitive_info": 1.0,
        "behavior": 1.0
    }
    res_crit = engine.calculate_risk(scores_crit)
    # 0.9 * 0.35 + 0.9 * 0.35 + 1.0 * 0.20 + 1.0 * 0.10 = 0.315 + 0.315 + 0.20 + 0.10 = 0.93
    assert abs(res_crit["risk_score"] - 0.93) < 0.001
    assert res_crit["risk_level"] == "CRITICAL"
