"""
Hybrid Risk Engine.

Aggregates individual component risk scores using configurable weights
and maps the final unified risk score to standard severity bands.
"""


class HybridRiskEngine:
    def __init__(self, weights: dict[str, float] | None = None):
        # Default weights matching specifications
        self.weights = weights or {
            "semantic_similarity": 0.35,
            "fact_leakage": 0.35,
            "sensitive_info": 0.20,
            "behavior": 0.10
        }
        
        # Verify weights sum to 1.0
        total_weight = sum(self.weights.values())
        if not (0.99 <= total_weight <= 1.01):
            raise ValueError(f"Risk weights must sum to approximately 1.0 (got {total_weight})")

    def calculate_risk(self, component_scores: dict[str, float]) -> dict:
        """
        Calculate weighted risk score and map to a standard risk level.
        Returns:
        - "risk_score": float
        - "risk_level": str
        """
        weighted_score = 0.0
        for comp, weight in self.weights.items():
            score = component_scores.get(comp, 0.0)
            weighted_score += score * weight

        # Cap score between 0.0 and 1.0
        weighted_score = max(0.0, min(1.0, weighted_score))

        # Map to risk levels: LOW, MEDIUM, HIGH, CRITICAL
        if weighted_score < 0.2:
            level = "LOW"
        elif weighted_score < 0.5:
            level = "MEDIUM"
        elif weighted_score < 0.8:
            level = "HIGH"
        else:
            level = "CRITICAL"

        return {
            "risk_score": weighted_score,
            "risk_level": level
        }
