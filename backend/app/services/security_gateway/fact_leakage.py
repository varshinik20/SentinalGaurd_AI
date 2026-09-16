"""
Fact Leakage Engine.

Performs pattern matching for numbers, dates, currencies, and entities.
Compares findings against protected database chunks to identify
unauthorized disclosure of factual pairings (like project + budget/date/personnel).
"""
import re


class FactLeakageEngine:
    def __init__(self):
        # Numeric quantity extraction (matches currency amounts, decimals, quantities with units, or multi-digit numbers)
        self.num_pattern = re.compile(
            r'[\$\u20A8\u20B9\u00A3\u20AC]\s*\d+(?:\.\d+)?|'
            r'\b\d+(?:\.\d+)?\s*(?:crore|million|billion|lakh|thousand|percent|%|usd|inr|eur)\b|'
            r'\b\d{2,}(?:\.\d+)?\b',
            re.IGNORECASE
        )
        
        # Date patterns (matches things like 17 September 2026, 17/09/2026, Sept 2026, etc.)
        self.date_pattern = re.compile(
            r'\b(?:\d{1,2}\s+)?(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sept|oct|nov|dec)\b(?:\s+\d{2,4})?|'
            r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
            re.IGNORECASE
        )

        # Entity patterns: Capitalized project names or specific protected keywords
        self.project_keywords = ["aurora", "omega", "sentinelguard", "project", "titan"]

    def extract_facts(self, text: str) -> dict:
        """
        Extract numbers, dates, and entities from a text block.
        """
        text_lower = text.lower()
        
        numbers = [num.strip() for num in self.num_pattern.findall(text) if num.strip()]
        dates = [dt.strip() for dt in self.date_pattern.findall(text) if dt.strip()]
        
        # Extract potential project identifiers
        found_projects = []
        for kw in self.project_keywords:
            if kw in text_lower:
                found_projects.append(kw)
        
        return {
            "numbers": list(set(numbers)),
            "dates": list(set(dates)),
            "projects": found_projects
        }

    def analyze(self, response_text: str, retrieved_contexts: list[dict]) -> dict:
        """
        Scan response_text and check for factual matching against retrieved contexts.
        retrieved_contexts is a list of FAISS search result dicts: [{"score": float, "metadata": dict}]
        """
        response_facts = self.extract_facts(response_text)
        resp_words = set(re.findall(r'\w+', response_text.lower()))
        
        evidence = []
        findings = []
        max_overlap_score = 0.0

        for ctx in retrieved_contexts:
            meta = ctx.get("metadata", {})
            content = meta.get("content", "")
            doc_name = meta.get("original_filename") or "Protected Document"
            classification = meta.get("classification", "CONFIDENTIAL")

            if not content:
                continue

            ctx_facts = self.extract_facts(content)
            ctx_words = set(re.findall(r'\w+', content.lower()))

            # Check overlaps
            leaked_numbers = [num for num in response_facts["numbers"] if num in ctx_facts["numbers"]]
            leaked_dates = [dt for dt in response_facts["dates"] if dt in ctx_facts["dates"]]
            
            # Word overlap calculation for entity/personnel disclosure
            common_words = resp_words.intersection(ctx_words) - {"the", "a", "an", "is", "by", "in", "on", "of", "and", "or", "to", "for", "with"}
            word_overlap_ratio = len(common_words) / max(len(ctx_words), 1)

            # Fact leakage occurs if number/date pairing OR significant word overlap with classified project chunk
            has_fact_leak = (
                ((leaked_numbers or leaked_dates) and response_facts["projects"]) or
                (classification in ("CONFIDENTIAL", "HIGHLY_CONFIDENTIAL", "RESTRICTED") and response_facts["projects"] and word_overlap_ratio > 0.3)
            )

            if has_fact_leak:
                overlap_score = 1.0 if (leaked_numbers or leaked_dates) else max(0.85, word_overlap_ratio)
                
                detail = {
                    "document_name": doc_name,
                    "classification": classification,
                    "leaked_numbers": leaked_numbers,
                    "leaked_dates": leaked_dates,
                    "matched_projects": response_facts["projects"]
                }
                findings.append(detail)
                
                desc = (
                    f"Factual correlation detected with '{doc_name}' ({classification}). "
                    f"Leaked entities/quantities: {leaked_numbers + leaked_dates if (leaked_numbers or leaked_dates) else response_facts['projects']}."
                )
                evidence.append({
                    "type": "FACT_LEAKAGE",
                    "severity": "CRITICAL" if classification in ("HIGHLY_CONFIDENTIAL", "RESTRICTED") else "HIGH",
                    "description": desc,
                    "details": detail
                })
                
                if overlap_score > max_overlap_score:
                    max_overlap_score = overlap_score

        return {
            "score": max_overlap_score,
            "findings": findings,
            "evidence": evidence
        }
