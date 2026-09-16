from app.services.security_gateway.fact_leakage import FactLeakageEngine


def test_fact_extraction():
    engine = FactLeakageEngine()
    text = "The budget for Aurora is 4.2 crore and the date is 17 September 2026. Also check $100."
    facts = engine.extract_facts(text)
    
    assert "4.2 crore" in facts["numbers"]
    assert "$100" in facts["numbers"]
    assert "17 September 2026" in facts["dates"]
    assert "aurora" in facts["projects"]
    assert "project" not in facts["projects"]  # only matches exact word list


def test_fact_leakage_analysis_positive():
    engine = FactLeakageEngine()
    
    # Mock retrieved context chunk
    context_chunk = {
        "score": 0.85,
        "metadata": {
            "content": "Project Aurora approval budget is 4.2 crore and scheduled for 17 September 2026.",
            "original_filename": "aurora_leak.txt",
            "classification": "HIGHLY_CONFIDENTIAL"
        }
    }
    
    # 1. Response contains both a matched number and a project keyword
    response_text = "We plan to deploy the Aurora project on 17 September 2026."
    results = engine.analyze(response_text, [context_chunk])
    
    assert results["score"] == 1.0
    assert len(results["findings"]) == 1
    assert results["findings"][0]["document_name"] == "aurora_leak.txt"
    assert "17 September 2026" in results["findings"][0]["leaked_dates"]
    assert len(results["evidence"]) == 1
    assert results["evidence"][0]["type"] == "FACT_LEAKAGE"
    assert results["evidence"][0]["severity"] == "CRITICAL"


def test_fact_leakage_analysis_negative():
    engine = FactLeakageEngine()
    
    context_chunk = {
        "score": 0.85,
        "metadata": {
            "content": "Project Aurora approval budget is 4.2 crore.",
            "original_filename": "aurora_leak.txt",
            "classification": "HIGHLY_CONFIDENTIAL"
        }
    }

    # Unrelated response with unrelated numbers and no project keywords
    response_text = "Today we spent $100 on team lunch."
    results = engine.analyze(response_text, [context_chunk])
    
    assert results["score"] == 0.0
    assert len(results["findings"]) == 0
    assert len(results["evidence"]) == 0
