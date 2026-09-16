"""
Behavior Engine.

Detects stateful anomalies like progressive extraction probes (jailbreaks or
recursive queries seeking confidential information over multiple steps).
"""
import re
from app.models.chat_message import ChatMessage


class BehaviorEngine:
    def __init__(self, history_window: int = 5):
        self.history_window = history_window
        # Keywords suggesting confidential corporate project inquiries
        self.probe_keywords = ["aurora", "omega", "budget", "launch", "secret", "financial", "crore"]

    def analyze(self, current_query: str, past_messages: list[ChatMessage]) -> dict:
        """
        Analyze current query against session message history.
        Returns a score (0.0 to 1.0) and evidence list.
        """
        # Filter only user messages in the active window
        user_queries = [
            msg.content.lower()
            for msg in past_messages
            if msg.sender == "user"
        ][-self.history_window:]
        
        # Add current query
        user_queries.append(current_query.lower())

        # Count how many queries in the active window contain probing keywords
        probe_count = 0
        matching_queries = []
        for q in user_queries:
            matched_kws = [kw for kw in self.probe_keywords if kw in q]
            if matched_kws:
                probe_count += 1
                matching_queries.append((q, matched_kws))

        # Calculate progressive extraction score (0.0 to 1.0)
        # 0-1 probes: 0.0 risk
        # 2 probes: 0.3 risk
        # 3 probes: 0.7 risk
        # 4+ probes: 1.0 risk (indicates systemic probing!)
        if probe_count <= 1:
            score = 0.0
        elif probe_count == 2:
            score = 0.3
        elif probe_count == 3:
            score = 0.7
        else:
            score = 1.0

        evidence = []
        findings = []

        if score >= 0.70:
            detail = {
                "probe_count": probe_count,
                "history_window": self.history_window,
                "matching_queries": [mq[0] for mq in matching_queries]
            }
            findings.append(detail)
            
            evidence.append({
                "type": "BEHAVIOR_ANOMALY",
                "severity": "CRITICAL" if score == 1.0 else "HIGH",
                "description": f"Stateful progressive extraction pattern detected ({probe_count} probes in active window).",
                "details": detail
            })

        return {
            "score": score,
            "findings": findings,
            "evidence": evidence
        }
