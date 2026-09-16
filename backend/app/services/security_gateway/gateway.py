"""
SentinelGuard Security Gateway.

Unifies all security analysis components: Semantic Similarity, Fact Leakage,
Sensitive Information, and Behavior, calculates hybrid risk, evaluates
policy rules, and strictly enforces all 5 decision contracts:
(ALLOW, WARN, REWRITE, BLOCK, HUMAN_REVIEW).
"""
import uuid
from app.models.user import User
from app.services.security_gateway.semantic_similarity import SemanticSimilarityEngine
from app.services.security_gateway.fact_leakage import FactLeakageEngine
from app.services.security_gateway.sensitive_information import SensitiveInformationAnalyzer
from app.services.security_gateway.behavior import BehaviorEngine
from app.services.security_gateway.hybrid_risk import HybridRiskEngine
from app.services.security_gateway.policy import PolicyEngine
from app.services.security_gateway.rewrite import RewriteEngine


class SentinelGuardGateway:
    SAFE_WITHHELD_MESSAGE = "This response has been withheld for security review."
    SAFE_BLOCKED_MESSAGE = "ACCESS DENIED: The requested response contains protected information and has been blocked by SentinelGuard AI."

    def __init__(self):
        self.semantic_engine = SemanticSimilarityEngine()
        self.fact_engine = FactLeakageEngine()
        self.sensitive_engine = SensitiveInformationAnalyzer()
        self.behavior_engine = BehaviorEngine()
        self.risk_engine = HybridRiskEngine()
        self.policy_engine = PolicyEngine()
        self.rewrite_engine = RewriteEngine()

    def _sanitize_evidence_for_release(self, evidence_list: list[dict]) -> list[dict]:
        """
        Sanitize evidence list so raw confidential credentials, credit cards,
        or document chunk texts are not exposed in user-facing responses.
        """
        sanitized = []
        for item in evidence_list:
            clean_item = {
                "type": item.get("type", "SECURITY_EVENT"),
                "severity": item.get("severity", "MEDIUM"),
                "description": item.get("description", "Security rule triggered."),
            }
            # Mask or sanitize details
            if "details" in item:
                orig_details = item["details"]
                clean_details = {}
                for k, v in orig_details.items():
                    if k in ("document_name", "classification", "severity", "matched_projects"):
                        clean_details[k] = v
                    elif k in ("leaked_numbers", "leaked_dates"):
                        clean_details[k] = ["[REDACTED_VALUE]"]
                    elif k in ("masked_text", "matches"):
                        clean_details[k] = "[MASKED_SENSITIVE_DATA]"
                    else:
                        clean_details[k] = "[PROTECTED]"
                clean_item["details"] = clean_details
            sanitized.append(clean_item)
        return sanitized

    async def inspect(
        self,
        query: str,
        response_text: str,
        user: User,
        retrieved_contexts: list[dict],
        past_messages: list
    ) -> dict:
        """
        Scan LLM query and response, calculate hybrid risk, evaluate policy rules,
        strictly enforce decision outcome contracts, and return sanitized security result.
        """
        # 1. Run Analysis Components on initial response
        sem_res = self.semantic_engine.analyze(response_text)
        fact_res = self.fact_engine.analyze(response_text, retrieved_contexts)
        sens_res = self.sensitive_engine.analyze(response_text)
        beh_res = self.behavior_engine.analyze(query, past_messages)

        # 2. Combine Scores for Hybrid Risk calculation
        component_scores = {
            "semantic_similarity": sem_res["max_score"],
            "fact_leakage": fact_res["score"],
            "sensitive_info": 1.0 if sens_res["contains_sensitive"] else 0.0,
            "behavior": beh_res["score"]
        }
        
        risk_res = self.risk_engine.calculate_risk(component_scores)
        risk_score = risk_res["risk_score"]
        risk_level = risk_res["risk_level"]

        # 3. Consolidate Evidence List
        evidence = []
        evidence.extend(sem_res["evidence"])
        evidence.extend(fact_res["evidence"])
        evidence.extend(sens_res["evidence"])
        evidence.extend(beh_res["evidence"])

        evidence_types = list(set(ev["type"] for ev in evidence))

        # Determine Max Classification from matched contexts
        max_class = "PUBLIC"
        class_order = self.policy_engine.CLASSIFICATION_ORDER
        for ctx in retrieved_contexts:
            meta = ctx["metadata"]
            classification = meta.get("classification", "PUBLIC")
            if class_order.get(classification, 0) > class_order.get(max_class, 0):
                max_class = classification

        # 4. Evaluate Security Policies
        policy_context = {
            "risk_level": risk_level,
            "user_role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "user_department": user.department,
            "max_classification": max_class,
            "evidence_types": evidence_types
        }
        
        policy_match = self.policy_engine.evaluate(policy_context)
        decision = policy_match["action"]

        # 5. Apply Strict Decision Contracts
        final_response = response_text

        if decision == "HUMAN_REVIEW":
            # Mandatory contract: NEVER release original response to normal user
            final_response = self.SAFE_WITHHELD_MESSAGE

        elif decision == "BLOCK":
            # Mandatory contract: NEVER release original response to normal user
            final_response = self.SAFE_BLOCKED_MESSAGE

        elif decision == "WARN":
            # Verify response doesn't contain unmasked sensitive information
            if sens_res["contains_sensitive"] or fact_res["score"] > 0.5:
                # Escalation to HUMAN_REVIEW if response contains protected facts
                decision = "HUMAN_REVIEW"
                final_response = self.SAFE_WITHHELD_MESSAGE
            else:
                final_response = response_text

        elif decision == "REWRITE":
            # Step A: Perform sanitization rewrite
            rewritten_text = self.rewrite_engine.rewrite(
                response_text=response_text,
                sens_res=sens_res,
                fact_res=fact_res,
                retrieved_contexts=retrieved_contexts
            )

            # Step B: FULL SECURITY RE-ANALYSIS on rewritten text
            recheck_sem = self.semantic_engine.analyze(rewritten_text)
            recheck_fact = self.fact_engine.analyze(rewritten_text, retrieved_contexts)
            recheck_sens = self.sensitive_engine.analyze(rewritten_text)

            recheck_scores = {
                "semantic_similarity": recheck_sem["max_score"],
                "fact_leakage": recheck_fact["score"],
                "sensitive_info": 1.0 if recheck_sens["contains_sensitive"] else 0.0,
                "behavior": beh_res["score"]
            }
            recheck_risk = self.risk_engine.calculate_risk(recheck_scores)
            recheck_evidence = []
            recheck_evidence.extend(recheck_sem["evidence"])
            recheck_evidence.extend(recheck_fact["evidence"])
            recheck_evidence.extend(recheck_sens["evidence"])
            recheck_evidence.extend(beh_res["evidence"])
            recheck_evidence_types = list(set(ev["type"] for ev in recheck_evidence))

            recheck_policy_ctx = {
                "risk_level": recheck_risk["risk_level"],
                "user_role": user.role.value if hasattr(user.role, "value") else str(user.role),
                "user_department": user.department,
                "max_classification": max_class,
                "evidence_types": recheck_evidence_types
            }
            recheck_policy_match = self.policy_engine.evaluate(recheck_policy_ctx)
            recheck_decision = recheck_policy_match["action"]

            # Step C: Evaluate re-analysis outcome
            if recheck_decision in ("ALLOW", "WARN", "REWRITE") and not recheck_sens["contains_sensitive"] and recheck_risk["risk_score"] < 0.5:
                final_response = rewritten_text
                decision = "REWRITE"
                risk_score = recheck_risk["risk_score"]
                risk_level = recheck_risk["risk_level"]
            else:
                # Rewrite failure: escalate to BLOCK or HUMAN_REVIEW with safe placeholder
                if recheck_decision == "HUMAN_REVIEW" or recheck_risk["risk_level"] == "HIGH":
                    decision = "HUMAN_REVIEW"
                    final_response = self.SAFE_WITHHELD_MESSAGE
                else:
                    decision = "BLOCK"
                    final_response = self.SAFE_BLOCKED_MESSAGE
                risk_score = max(risk_score, recheck_risk["risk_score"])
                risk_level = recheck_risk["risk_level"]

        elif decision == "ALLOW":
            final_response = response_text

        request_id = str(uuid.uuid4())
        sanitized_evidence = self._sanitize_evidence_for_release(evidence)

        return {
            "response": final_response,
            "decision": decision,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "request_id": request_id,
            "security_summary": {
                "components": component_scores,
                "policy": {
                    "name": policy_match["name"],
                    "description": policy_match["description"]
                },
                "evidence": sanitized_evidence
            }
        }
