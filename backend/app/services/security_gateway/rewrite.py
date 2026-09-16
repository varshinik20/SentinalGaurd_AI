"""
Rewrite Engine for SentinelGuard AI.

Performs comprehensive sanitization of sensitive values, PII, leaked facts,
financial quantities, dates, and protected entity references.
"""
import re


class RewriteEngine:
    def __init__(self):
        # Numeric & currency patterns ($18 million, 42 crore, ₹100, $15.5)
        self.num_pattern = re.compile(
            r'[\$\u20A8\u20B9\u00A3\u20AC]\s*\d+(?:\.\d+)?(?:\s*(?:crore|million|billion|lakh))?|'
            r'\b(?:\d+(?:\.\d+)?)\s*(?:crore|million|billion|lakh|thousand)\b',
            re.IGNORECASE
        )

        # Date patterns (17 September 2026, 17/09/2026, Sept 2026, etc.)
        self.date_pattern = re.compile(
            r'\b(?:\d{1,2}\s+)?(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sept|oct|nov|dec)(?:\s+\d{2,4})?\b|'
            r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
            re.IGNORECASE
        )

        # Secret / API Key / Password patterns
        self.secret_pattern = re.compile(
            r'\b[A-Za-z0-9_\-]{20,}\b|'
            r'(?:password|secret|key|token|api_key)\s*[:=]\s*[^\s]+',
            re.IGNORECASE
        )

    def rewrite(
        self,
        response_text: str,
        sens_res: dict,
        fact_res: dict,
        retrieved_contexts: list[dict]
    ) -> str:
        """
        Produce a sanitized version of response_text by masking PII, leaked facts,
        numbers, dates, and protected pairings.
        """
        # 1. Start with PII masking result if available
        rewritten = sens_res.get("masked_text", response_text)

        # 2. Mask leaked numbers and dates identified by Fact Leakage Engine
        for finding in fact_res.get("findings", []):
            for num in finding.get("leaked_numbers", []):
                if num and num in rewritten:
                    rewritten = rewritten.replace(num, "[MASKED_QUANTITY]")
            for dt in finding.get("leaked_dates", []):
                if dt and dt in rewritten:
                    rewritten = rewritten.replace(dt, "[MASKED_DATE]")

        # 3. Comprehensive Regex Redaction for Financial Amounts & Quantities
        rewritten = self.num_pattern.sub("[MASKED_QUANTITY]", rewritten)

        # 4. Comprehensive Regex Redaction for Dates
        rewritten = self.date_pattern.sub("[MASKED_DATE]", rewritten)

        # 5. Mask Secrets and Credentials
        rewritten = self.secret_pattern.sub("[REDACTED_SECRET]", rewritten)

        return rewritten
