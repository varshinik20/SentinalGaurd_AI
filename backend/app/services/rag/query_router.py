"""
Query Router Service.

Classifies incoming user queries into Knowledge Domains:
1. GENERAL_KNOWLEDGE: Public entities, concepts, math, programming, technology, public company questions.
2. PROTECTED_KNOWLEDGE: Internal organizational secrets, private project budgets, internal leads, confidential deployment dates, contract terms.
3. MIXED: Combines a public general question with a protected organizational request.
4. UNKNOWN: Ambiguous queries.
"""
import re
import logging
from app.models.user import User

logger = logging.getLogger(__name__)

# Keywords / patterns indicating organizational internal scope
ORGANIZATIONAL_SCOPE_PATTERNS = [
    r"\bour\b", r"\bmy company\b", r"\bmy organization\b", r"\binternal\b", 
    r"\bconfidential\b", r"\bsecret\b", r"\bprivate agreement\b", r"\bour contract\b",
    r"\bour agreement\b", r"\bour account manager\b", r"\bour discount\b"
]

# Protected project / asset identifiers
PROTECTED_PROJECTS = ["titan", "aurora", "stealth"]

# Protected fact target attributes
PROTECTED_ATTRIBUTES = [
    "budget", "funding", "cost", "allocation", "allocated", "launch date", 
    "launch", "lead", "manager", "who leads", "who is in charge", "owner", 
    "contract value", "contract terms", "secret key", "access key", "credentials", "password"
]

# General knowledge educational / conceptual indicators
GENERAL_CONCEPTUAL_PATTERNS = [
    r"^what is\s+(a|an|the)?\s*(project\s+budget|budgeting|financial\s+planning|machine\s+learning|rag|jwt|python|faiss|quantum|string|rest|graphql|encryption|zero\tust|rbac|amazon|google|microsoft|flipkart|apple|meta|tesla|nvidia|openai|sap|ibm|oracle|netflix|adobe|salesforce|infosys|tcs|wipro|accenture)",
    r"^explain\s+", r"^how does\s+", r"^compare\s+", r"^write\s+python", r"^tell me about\s+(amazon|google|microsoft|flipkart|apple|meta|tesla|nvidia|openai|sap|ibm|oracle|netflix|adobe|salesforce|infosys|tcs|wipro|accenture)"
]


class QueryRouter:
    def __init__(self):
        pass

    def route(self, query_text: str, user: User | None = None) -> dict:
        """
        Analyze query_text to determine knowledge routing domain.
        """
        q_lower = query_text.lower().strip()

        has_general = False
        has_protected = False
        protected_target = None
        general_target = None

        # 1. Check for Protected Facts / Project Targets
        for proj in PROTECTED_PROJECTS:
            if proj in q_lower:
                # Check if query asks for protected attribute of the project
                if any(attr in q_lower for attr in ["budget", "funding", "cost", "allocate", "money", "approved", "launch", "date", "when", "lead", "manager", "who", "in charge", "owner", "region"]):
                    has_protected = True
                    protected_target = f"Project {proj.capitalize()}"
                    break

        # 2. Check for Organizational Contract / Private Data Patterns
        if not has_protected:
            if any(re.search(pat, q_lower) for pat in ORGANIZATIONAL_SCOPE_PATTERNS):
                if any(attr in q_lower for attr in ["contract", "agreement", "value", "terms", "discount", "account manager", "key", "secret", "budget"]):
                    has_protected = True
                    protected_target = "Internal Organizational Agreement/Data"
            elif any(k in q_lower for k in ["secret key", "access key", "aws_secret", "production password"]):
                has_protected = True
                protected_target = "Credentials & Secrets"

        # 3. Check for General Knowledge
        # If query asks about public entity or general concept
        public_companies = [
            "amazon", "flipkart", "google", "microsoft", "apple", "meta", "tesla", 
            "nvidia", "openai", "sap", "ibm", "oracle", "netflix", "adobe", 
            "salesforce", "infosys", "tcs", "wipro", "accenture"
        ]
        
        # Public entity check: ensure it's not purely a contract/protected qualifier (e.g., "our Amazon contract")
        is_pure_contract_qualifier = bool(re.search(r"\bour\s+(amazon|google|microsoft|flipkart|apple|meta|tesla|nvidia|openai|sap|ibm|oracle)\s+(contract|agreement|terms|account manager|discount|budget|key)\b", q_lower))
        is_public_entity = any(re.search(r"\b" + comp + r"\b", q_lower) for comp in public_companies) and not is_pure_contract_qualifier

        is_general_concept = any(re.search(pat, q_lower) for pat in GENERAL_CONCEPTUAL_PATTERNS) or any(w in q_lower for w in ["machine learning", "transformers", "quantum computing", "string theory", "python", "rest api", "graphql", "jwt", "rbac", "zero trust", "encryption", "faiss", "rag"])

        # Check if generic "what is a budget" or "what is budgeting"
        is_generic_budgeting = bool(re.search(r"\bwhat is (a |an )?(project )?budget(ing)?\b", q_lower) or re.search(r"\bexplain (financial planning|project budgeting)\b", q_lower))
        if is_generic_budgeting and not has_protected:
            is_general_concept = True

        if is_public_entity or is_general_concept:
            has_general = True
            general_target = "Public/General Knowledge"

        # 4. Synthesize Domain Verdict
        if has_protected and has_general:
            domain = "MIXED"
        elif has_protected:
            domain = "PROTECTED_KNOWLEDGE"
        elif has_general:
            domain = "GENERAL_KNOWLEDGE"
        else:
            # Default fallback: if no protected pattern detected, treat as GENERAL_KNOWLEDGE
            domain = "GENERAL_KNOWLEDGE"

        return {
            "domain": domain,
            "has_protected": has_protected,
            "has_general": has_general,
            "protected_target": protected_target,
            "general_target": general_target
        }
