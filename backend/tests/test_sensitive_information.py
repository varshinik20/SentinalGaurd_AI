from app.services.security_gateway.sensitive_information import SensitiveInformationAnalyzer


def test_sensitive_info_extraction_and_masking():
    analyzer = SensitiveInformationAnalyzer()

    # 1. Test Email Masking
    text_email = "Please contact support at admin@sentinelguard.ai for assistance."
    res = analyzer.analyze(text_email)
    assert res["contains_sensitive"] is True
    assert "admin@sentinelguard.ai" in [f["value"] for f in res["findings"]]
    assert res["masked_text"] == "Please contact support at [MASKED_EMAIL] for assistance."
    assert res["evidence"][0]["type"] == "SENSITIVE_INFORMATION"
    assert res["evidence"][0]["severity"] == "HIGH"

    # 2. Test Credit Card Masking
    text_cc = "My visa number is 4111-2222-3333-4444."
    res_cc = analyzer.analyze(text_cc)
    assert res_cc["contains_sensitive"] is True
    assert "4111-2222-3333-4444" in [f["value"] for f in res_cc["findings"]]
    assert res_cc["masked_text"] == "My visa number is [MASKED_CREDIT_CARD]."
    assert res_cc["evidence"][0]["severity"] == "CRITICAL"

    # 3. Test Credentials/Secrets Masking
    text_aws = "The deploy key: AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    res_aws = analyzer.analyze(text_aws)
    assert res_aws["contains_sensitive"] is True
    assert "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" in [f["value"] for f in res_aws["findings"]]
    assert res_aws["masked_text"] == "The deploy key: [MASKED_AWS_SECRET]"

    # 4. Test Aadhaar Masking
    text_aadhaar = "My Aadhaar card number is 1234 5678 9012."
    res_aad = analyzer.analyze(text_aadhaar)
    assert res_aad["contains_sensitive"] is True
    assert "1234 5678 9012" in [f["value"] for f in res_aad["findings"]]
    assert res_aad["masked_text"] == "My Aadhaar card number is [MASKED_AADHAAR]."
