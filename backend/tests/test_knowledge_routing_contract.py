"""
Knowledge Routing & Security Contract Automated Test Suite.

Verifies strict domain separation between General AI Knowledge and
Protected Organizational Knowledge across all 15 required test scenarios.
"""
import pytest
import uuid
from app.models.user import User, Role
from app.services.rag.query_router import QueryRouter
from app.services.rag.pre_query_authorizer import PreQueryAuthorizer
from app.services.rag.providers.local_provider import LocalProvider
from app.services.rag.rag_service import RAGService


@pytest.fixture
def mock_unauthorized_user():
    return User(
        id=uuid.uuid4(),
        email="employee@sentinelguard.ai",
        full_name="Standard Employee",
        role=Role.EMPLOYEE,
        department="Marketing",
        is_active=True
    )


@pytest.fixture
def mock_authorized_admin():
    return User(
        id=uuid.uuid4(),
        email="admin@sentinelguard.ai",
        full_name="System Admin",
        role=Role.ADMIN,
        department="Platform",
        is_active=True
    )


def test_1_general_knowledge_machine_learning(mock_unauthorized_user):
    router = QueryRouter()
    info = router.route("What is machine learning?", mock_unauthorized_user)
    assert info["domain"] == "GENERAL_KNOWLEDGE"
    assert not info["has_protected"]


def test_2_general_knowledge_rag(mock_unauthorized_user):
    router = QueryRouter()
    info = router.route("Explain RAG.", mock_unauthorized_user)
    assert info["domain"] == "GENERAL_KNOWLEDGE"
    assert not info["has_protected"]


def test_3_general_knowledge_human_review_definition(mock_unauthorized_user):
    router = QueryRouter()
    info = router.route("Explain HUMAN_REVIEW.", mock_unauthorized_user)
    assert info["domain"] == "GENERAL_KNOWLEDGE"
    assert not info["has_protected"]


def test_4_general_knowledge_generic_budgeting(mock_unauthorized_user):
    router = QueryRouter()
    info = router.route("What is a project budget?", mock_unauthorized_user)
    assert info["domain"] == "GENERAL_KNOWLEDGE"
    assert not info["has_protected"]


def test_5_general_knowledge_financial_planning(mock_unauthorized_user):
    router = QueryRouter()
    info = router.route("Explain financial planning.", mock_unauthorized_user)
    assert info["domain"] == "GENERAL_KNOWLEDGE"
    assert not info["has_protected"]


def test_6_public_company_amazon(mock_unauthorized_user):
    router = QueryRouter()
    info = router.route("What is Amazon?", mock_unauthorized_user)
    assert info["domain"] == "GENERAL_KNOWLEDGE"
    assert not info["has_protected"]


def test_7_public_company_comparison(mock_unauthorized_user):
    router = QueryRouter()
    info = router.route("Compare Amazon and Flipkart.", mock_unauthorized_user)
    assert info["domain"] == "GENERAL_KNOWLEDGE"
    assert not info["has_protected"]


def test_8_protected_knowledge_titan_budget(mock_unauthorized_user):
    router = QueryRouter()
    info = router.route("What is Project Titan's budget?", mock_unauthorized_user)
    assert info["has_protected"]
    
    authorizer = PreQueryAuthorizer()
    auth = authorizer.authorize("What is Project Titan's budget?", mock_unauthorized_user, info)
    assert not auth["is_authorized"]
    assert auth["action"] == "BLOCK"
    assert "ACCESS DENIED" in auth["response"]


def test_9_protected_knowledge_titan_funding(mock_unauthorized_user):
    router = QueryRouter()
    info = router.route("How much funding was allocated to Titan?", mock_unauthorized_user)
    assert info["has_protected"]
    
    authorizer = PreQueryAuthorizer()
    auth = authorizer.authorize("How much funding was allocated to Titan?", mock_unauthorized_user, info)
    assert not auth["is_authorized"]
    assert auth["action"] == "BLOCK"


def test_10_protected_knowledge_titan_launch_date(mock_unauthorized_user):
    router = QueryRouter()
    info = router.route("What is Titan's launch date?", mock_unauthorized_user)
    assert info["has_protected"]
    
    authorizer = PreQueryAuthorizer()
    auth = authorizer.authorize("What is Titan's launch date?", mock_unauthorized_user, info)
    assert not auth["is_authorized"]
    assert auth["action"] == "BLOCK"


def test_11_protected_knowledge_titan_lead(mock_unauthorized_user):
    router = QueryRouter()
    info = router.route("Who is the internal lead for Titan?", mock_unauthorized_user)
    assert info["has_protected"]
    
    authorizer = PreQueryAuthorizer()
    auth = authorizer.authorize("Who is the internal lead for Titan?", mock_unauthorized_user, info)
    assert not auth["is_authorized"]
    assert auth["action"] == "BLOCK"


def test_12_protected_knowledge_private_contract(mock_unauthorized_user):
    router = QueryRouter()
    info = router.route("What is our Amazon contract value?", mock_unauthorized_user)
    assert info["has_protected"]
    
    authorizer = PreQueryAuthorizer()
    auth = authorizer.authorize("What is our Amazon contract value?", mock_unauthorized_user, info)
    assert not auth["is_authorized"]
    assert auth["action"] == "BLOCK"


def test_13_semantic_paraphrase_titan_money(mock_unauthorized_user):
    router = QueryRouter()
    info = router.route("Approximately how much money is Titan receiving?", mock_unauthorized_user)
    assert info["has_protected"]


def test_14_mixed_query_routing(mock_unauthorized_user):
    router = QueryRouter()
    info = router.route("Explain project budgeting and tell me Titan's budget.", mock_unauthorized_user)
    assert info["domain"] == "MIXED"
    assert info["has_general"]
    assert info["has_protected"]


def test_15_authorized_access(mock_authorized_admin):
    router = QueryRouter()
    info = router.route("What is Project Titan's budget?", mock_authorized_admin)
    authorizer = PreQueryAuthorizer()
    auth = authorizer.authorize("What is Project Titan's budget?", mock_authorized_admin, info)
    assert auth["is_authorized"]


def test_16_critical_titan_watches_collection(mock_unauthorized_user):
    router = QueryRouter()
    info = router.route("tell me the watch collection in titan", mock_unauthorized_user)
    assert info["domain"] == "GENERAL_KNOWLEDGE"
    assert not info["has_protected"]
    
    authorizer = PreQueryAuthorizer()
    auth = authorizer.authorize("tell me the watch collection in titan", mock_unauthorized_user, info)
    assert auth["is_authorized"]
    assert auth["action"] == "ALLOW"
    
    provider = LocalProvider()
    res = provider.generate("tell me the watch collection in titan")
    assert "Titan Company Limited" in res or "Titan Watches" in res
    assert "Raga" in res or "Edge" in res
    assert "I'd be happy to help with" not in res
    assert "Feel free to ask" not in res
