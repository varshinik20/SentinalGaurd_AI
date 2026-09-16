"""
RAG Service.

Orchestrates query embedding, permission-aware vector context retrieval,
prompt assembly, and LLM text generation across different providers.
"""
import uuid
import logging
from app.models.user import User
from app.services.rag.retriever import PermissionAwareRetriever
from app.services.rag.providers.local_provider import LocalProvider
from app.services.rag.providers.ollama_provider import OllamaProvider
from app.services.rag.providers.openai_provider import OpenAIProvider
from app.services.rag.providers.gemini_provider import GeminiProvider
from app.services.rag.providers.anthropic_provider import AnthropicProvider

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        self.retriever = PermissionAwareRetriever()
        self.providers = {
            "local": LocalProvider,
            "offline": LocalProvider,
            "ollama": OllamaProvider,
            "openai": OpenAIProvider,
            "gemini": GeminiProvider,
            "anthropic": AnthropicProvider,
        }

    def _get_provider(self, provider_name: str | None) -> str:
        """Resolve LLM provider name to standard key."""
        if not provider_name:
            return "local"
        name = provider_name.lower().strip()
        return name if name in self.providers else "local"

    async def generate_response(
        self,
        query_text: str,
        user: User,
        db_session,
        session_id: uuid.UUID,
        provider_name: str | None = None
    ) -> dict:
        """
        Orchestrate retrieval, context assembly, model completion, and security validation.
        """
        from app.repositories.chat_session_repository import ChatSessionRepository
        from app.models.chat_message import ChatMessage
        from app.services.security_gateway.gateway import SentinelGuardGateway

        # 0. Retrieve conversation history
        repo = ChatSessionRepository(db_session)
        past_messages = await repo.list_messages(session_id)

        # 0.5 Query Domain Routing & Pre-Query Authorization
        from app.services.rag.query_router import QueryRouter
        from app.services.rag.pre_query_authorizer import PreQueryAuthorizer

        router = QueryRouter()
        route_info = router.route(query_text, user)
        authorizer = PreQueryAuthorizer()

        # Pre-query authorization for protected requests
        auth_info = authorizer.authorize(query_text, user, route_info)
        if not auth_info["is_authorized"] and route_info["domain"] == "PROTECTED_KNOWLEDGE":
            request_id = str(uuid.uuid4())
            block_response = {
                "response": auth_info["response"],
                "decision": "BLOCK",
                "risk_score": 0.95,
                "risk_level": "CRITICAL",
                "request_id": request_id,
                "security_summary": {
                    "components": {"semantic_similarity": 0.9, "fact_leakage": 0.0, "sensitive_info": 0.0, "behavior": 0.0},
                    "policy": {
                        "name": "PRE_QUERY_AUTHORIZATION_POLICY",
                        "description": auth_info["reason"]
                    },
                    "evidence": []
                }
            }
            # Log event to database
            from app.services.security_gateway.evidence import EvidenceEngine
            evidence_engine = EvidenceEngine(db_session)
            await evidence_engine.log_security_event(
                request_id=request_id,
                session_id=session_id,
                user_id=user.id,
                query=query_text,
                raw_response="",
                inspection_result=block_response
            )
            # Save user message
            user_msg = ChatMessage(session_id=session_id, sender="user", content=query_text)
            await repo.save_message(user_msg)
            # Save AI blocked response
            ai_msg = ChatMessage(
                session_id=session_id,
                sender="ai",
                content=block_response["response"],
                security_decision="BLOCK",
                risk_score=0.95
            )
            await repo.save_message(ai_msg)
            return block_response

        # 1. Retrieve matching chunks ONLY if authorized for protected knowledge domain
        retrieved_chunks = []
        if route_info["domain"] in ("PROTECTED_KNOWLEDGE", "MIXED") and auth_info["is_authorized"]:
            retrieved_chunks = self.retriever.retrieve(query_text, user, top_k=3)
        
        # 2. Build context block
        context_lines = []
        for i, chunk in enumerate(retrieved_chunks):
            content = chunk["metadata"]["content"]
            context_lines.append(f"[{i+1}] {content}")
        
        context = "\n".join(context_lines)

        # 3. Construct Prompts
        system_prompt = (
            "You are a professional corporate AI assistant. Answer the user's question "
            "using the provided context snippets where possible. If the context does not "
            "contain the answer, rely on your general knowledge but decline to answer if "
            "the query target seems confidential."
        )

        prompt = f"Context snippet(s):\n{context}\n\nUser Question:\n{query_text}"

        # 4. Invoke LLM Provider
        provider_key = self._get_provider(provider_name)
        provider_class = self.providers[provider_key]
        provider = provider_class()
        
        # Generate raw response
        try:
            raw_response = provider.generate(prompt, system_prompt)
        except Exception as e:
            logger.warning(
                "Provider '%s' generation failed: %s. Using Smart Local Synthesis fallback.",
                provider_key,
                str(e),
            )
            # Seamless fallback to intelligent local contextual synthesis
            fallback_provider = LocalProvider()
            raw_response = fallback_provider.generate(prompt, system_prompt)

        # Handle MIXED query unauthorized refusal appending
        if route_info["domain"] == "MIXED" and not auth_info["is_authorized"]:
            raw_response = raw_response.strip() + "\n\nI cannot provide protected internal information for this request."

        # 5. Run Security Inspections and policy evaluation
        gateway = SentinelGuardGateway()
        result = await gateway.inspect(
            query=query_text,
            response_text=raw_response,
            user=user,
            retrieved_contexts=retrieved_chunks,
            past_messages=past_messages
        )

        # 5.5 Dispatch to Evidence Engine
        from app.services.security_gateway.evidence import EvidenceEngine
        evidence_engine = EvidenceEngine(db_session)
        await evidence_engine.log_security_event(
            request_id=result["request_id"],
            session_id=session_id,
            user_id=user.id,
            query=query_text,
            raw_response=raw_response,
            inspection_result=result
        )

        # 6. Persist conversation history to database
        # Save user message
        user_msg = ChatMessage(
            session_id=session_id,
            sender="user",
            content=query_text
        )
        await repo.save_message(user_msg)

        # Save AI response
        ai_msg = ChatMessage(
            session_id=session_id,
            sender="ai",
            content=result["response"],
            security_decision=result["decision"],
            risk_score=result["risk_score"]
        )
        await repo.save_message(ai_msg)
        
        return result
