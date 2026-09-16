"""
Sensitive Information Analyzer.

Scans texts for PII, credentials, secrets, and credit cards using regexes.
Provides masking utilities and evidence generation.
"""
import re


class SensitiveInformationAnalyzer:
    def __init__(self):
        # Define regex patterns for sensitive data
        self.patterns = {
            "EMAIL": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            "PHONE": re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
            "CREDIT_CARD": re.compile(r'\b(?:\d[ -]*?){13,16}\b'),
            "AWS_SECRET": re.compile(r'\bAWS_SECRET_ACCESS_KEY\s*=\s*[A-Za-z0-9/+=]{20,60}\b', re.IGNORECASE),
            "GENERIC_SECRET": re.compile(r'\b(?:api_key|apikey|token|secret)\s*[:=]\s*["\']?[A-Za-z0-9\-_]{16,64}["\']?\b', re.IGNORECASE),
            "SSN": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            "AADHAAR": re.compile(r'\b\d{4}\s\d{4}\s\d{4}\b')
        }

    def analyze(self, text: str) -> dict:
        """
        Analyze the text for sensitive information.
        Returns:
        - "contains_sensitive": bool
        - "findings": list of match details
        - "masked_text": string with masked values
        - "evidence": list of security evidence objects
        """
        findings = []
        evidence = []
        masked_text = text

        for label, pattern in self.patterns.items():
            matches = list(set(pattern.findall(text)))
            for match in matches:
                # Add finding
                finding = {
                    "type": label,
                    "value": match
                }
                findings.append(finding)

                # Mask value in text
                mask = f"[MASKED_{label}]"
                masked_text = masked_text.replace(match, mask)

                # Add evidence item
                evidence.append({
                    "type": "SENSITIVE_INFORMATION",
                    "severity": "CRITICAL" if label in ("CREDIT_CARD", "AWS_SECRET", "GENERIC_SECRET", "SSN") else "HIGH",
                    "description": f"Sensitive data type '{label}' detected in text.",
                    "details": {"type": label}
                })

        return {
            "contains_sensitive": len(findings) > 0,
            "findings": findings,
            "masked_text": masked_text,
            "evidence": evidence
        }
