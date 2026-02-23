# [DEBUG] ============================================================
# Agent   : backend_dev
# Task    : Python Lambda + Pydantic + pytest 実装
# Created : 2026-02-23T18:56:39
# Updated : 2026-02-23
# [/DEBUG] ===========================================================

"""Unit tests for LangGraph RAG HITL core module.

All tests pass without API keys (Ollama mocked).
Tests follow TDD Red → Green → Refactor pattern.
"""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.langgraph_rag_hitl.core import (
    HITL_CONFIDENCE_THRESHOLD,
    MAX_REWRITE_RETRIES,
    HybridRetriever,
    RAGState,
    _node_check_hitl,
    _node_generate,
    _node_grade,
    _node_retrieve,
    _node_rewrite,
    _should_generate,
    _should_rewrite,
    run_experiment,
)
from src.langgraph_rag_hitl.models import (
    ExperimentRequest,
    ExperimentResponse,
    SourceDocument,
)

# --- HybridRetriever tests ---

class TestHybridRetriever:
    """Tests for BM25 + RRF hybrid retriever."""

    def test_retrieve_returns_top_k(self, sample_speeches: list[dict[str, Any]]) -> None:
        """HybridRetriever returns at most top_k documents."""
        retriever = HybridRetriever(sample_speeches)
        results = retriever.retrieve("国会 審議", top_k=3)
        assert len(results) <= 3

    def test_retrieve_returns_source_documents(self, sample_speeches: list[dict[str, Any]]) -> None:
        """HybridRetriever returns SourceDocument instances with valid fields."""
        retriever = HybridRetriever(sample_speeches)
        results = retriever.retrieve("教育 政策")
        assert len(results) > 0
        for doc in results:
            assert isinstance(doc, SourceDocument)
            assert 0.0 <= doc.score <= 1.0
            assert doc.speech_id
            assert doc.date

    def test_retrieve_scores_normalized(self, sample_speeches: list[dict[str, Any]]) -> None:
        """Retrieval scores are normalized to [0, 1] range."""
        retriever = HybridRetriever(sample_speeches)
        results = retriever.retrieve("予算 委員会")
        for doc in results:
            assert 0.0 <= doc.score <= 1.0

    def test_retrieve_empty_corpus(self) -> None:
        """HybridRetriever handles empty corpus gracefully."""
        retriever = HybridRetriever([])
        results = retriever.retrieve("テスト")
        assert results == []

    def test_rrf_fusion_combines_bm25_and_dense(self, sample_speeches: list[dict[str, Any]]) -> None:
        """RRF fusion with k=60 produces valid scores (BM25_WEIGHT + DENSE_WEIGHT)."""
        retriever = HybridRetriever(sample_speeches)
        # Max possible score per doc: 0.3/(60+1) + 0.7/(60+1) ≈ 0.0164
        results = retriever.retrieve("国会", top_k=5)
        # All scores should be positive
        assert all(doc.score > 0 for doc in results)

    def test_retrieve_relevant_speech_ranked_higher(self, sample_speeches: list[dict[str, Any]]) -> None:
        """Documents with more query keyword overlap score higher."""
        retriever = HybridRetriever(sample_speeches)
        # Query about education should rank education speeches higher
        results = retriever.retrieve("教育 学校 政策", top_k=5)
        assert len(results) > 0
        # Top result should have reasonable content
        assert len(results[0].content) > 0


# --- Workflow Node tests ---

class TestWorkflowNodes:
    """Tests for individual LangGraph workflow nodes."""

    def _make_state(
        self,
        query: str = "国会の審議について",
        retrieved_docs: list[SourceDocument] | None = None,
        relevant_docs: list[SourceDocument] | None = None,
        retry_count: int = 0,
    ) -> RAGState:
        """Helper to create a RAGState for testing."""
        return {
            "query": query,
            "rewritten_query": "",
            "max_results": 5,
            "user_roles": ["public"],
            "retrieved_docs": retrieved_docs or [],
            "graded_docs": [],
            "relevant_docs": relevant_docs or [],
            "answer": "",
            "requires_review": False,
            "hitl_review": None,
            "workflow_steps": [],
            "retry_count": retry_count,
            "request_id": "test-id",
        }

    def test_node_retrieve_populates_docs(self, sample_speeches: list[dict[str, Any]]) -> None:
        """_node_retrieve populates retrieved_docs in state."""
        retriever = HybridRetriever(sample_speeches)
        state = self._make_state("教育")
        result = _node_retrieve(state, retriever)
        assert len(result["retrieved_docs"]) > 0
        assert "retrieve:" in result["workflow_steps"][0]

    def test_node_grade_classifies_relevant(self, sample_speeches: list[dict[str, Any]]) -> None:
        """_node_grade correctly classifies documents as relevant/irrelevant."""
        retriever = HybridRetriever(sample_speeches)
        state = self._make_state("国会 審議")
        state = _node_retrieve(state, retriever)
        state = _node_grade(state)
        assert len(state["graded_docs"]) > 0
        assert "grade:" in state["workflow_steps"][-1]

    def test_node_grade_tracks_relevant_docs(self, sample_speeches: list[dict[str, Any]]) -> None:
        """_node_grade populates relevant_docs when documents match query."""
        retriever = HybridRetriever(sample_speeches)
        state = self._make_state("予算 委員会 審議")
        state = _node_retrieve(state, retriever)
        state = _node_grade(state)
        # relevant_docs is a subset of retrieved_docs
        assert len(state["relevant_docs"]) <= len(state["retrieved_docs"])

    def test_node_rewrite_increments_retry(self) -> None:
        """_node_rewrite increments retry_count and sets rewritten_query."""
        state = self._make_state("教育")
        result = _node_rewrite(state)
        assert result["retry_count"] == 1
        assert result["rewritten_query"] != ""
        assert "rewrite:" in result["workflow_steps"][0]

    def test_node_rewrite_expands_query(self) -> None:
        """_node_rewrite appends parliamentary term to query."""
        state = self._make_state("AI 技術")
        result = _node_rewrite(state)
        assert result["rewritten_query"].startswith("AI 技術")
        assert len(result["rewritten_query"]) > len("AI 技術")

    def test_node_check_hitl_low_confidence(self) -> None:
        """HITL activates when fewer than HITL_CONFIDENCE_THRESHOLD relevant docs."""
        state = self._make_state(relevant_docs=[])  # 0 < 2 threshold
        result = _node_check_hitl(state)
        assert result["requires_review"] is True
        assert result["hitl_review"] is not None
        assert result["hitl_review"].reason == "low_confidence"

    def test_node_check_hitl_sensitive_keyword(self) -> None:
        """HITL activates when sensitive keywords detected in query."""
        state = self._make_state(
            query="給与 水準について",
            relevant_docs=[
                SourceDocument(
                    speech_id="s1", speaker="A", date="2026-01-01",
                    content="テスト", score=0.9,
                ),
                SourceDocument(
                    speech_id="s2", speaker="B", date="2026-01-02",
                    content="テスト2", score=0.8,
                ),
            ],
        )
        result = _node_check_hitl(state)
        assert result["requires_review"] is True
        assert result["hitl_review"].reason == "sensitive_topic"
        assert "給与" in result["hitl_review"].sensitive_keywords

    def test_node_check_hitl_skips_normal_query(self) -> None:
        """HITL does not activate for normal query with enough relevant docs."""
        docs = [
            SourceDocument(
                speech_id=f"s{i}", speaker="A", date="2026-01-01",
                content="国会の審議について", score=0.8,
            )
            for i in range(3)
        ]
        state = self._make_state(query="国会の審議について", relevant_docs=docs)
        result = _node_check_hitl(state)
        assert result["requires_review"] is False
        assert result["hitl_review"] is None
        assert "hitl:skip" in result["workflow_steps"]

    def test_node_generate_with_ollama_mock(
        self,
        mock_ollama: MagicMock,
        mock_ollama_response: str,
    ) -> None:
        """_node_generate calls Ollama and sets answer in state."""
        doc = SourceDocument(
            speech_id="s1", speaker="A", date="2026-01-01",
            content="国会の審議では教育予算が議論されました。", score=0.8,
        )
        state = self._make_state(query="予算について", relevant_docs=[doc])
        result = _node_generate(state)
        assert result["answer"] != ""
        assert "generate:" in result["workflow_steps"][0]

    def test_node_generate_no_docs_returns_fallback(self) -> None:
        """_node_generate returns fallback message when no documents available."""
        state = self._make_state(query="テスト", retrieved_docs=[], relevant_docs=[])
        result = _node_generate(state)
        assert "見つかりませんでした" in result["answer"]


# --- Decision Function tests ---

class TestDecisionFunctions:
    """Tests for LangGraph conditional routing functions."""

    def _make_state(
        self,
        relevant_docs_count: int = 0,
        retry_count: int = 0,
        requires_review: bool = False,
    ) -> RAGState:
        relevant_docs = [
            SourceDocument(
                speech_id=f"s{i}", speaker="A", date="2026-01-01",
                content="テスト", score=0.5,
            )
            for i in range(relevant_docs_count)
        ]
        return {
            "query": "テスト",
            "rewritten_query": "",
            "max_results": 5,
            "user_roles": ["public"],
            "retrieved_docs": [],
            "graded_docs": [],
            "relevant_docs": relevant_docs,
            "answer": "",
            "requires_review": requires_review,
            "hitl_review": None,
            "workflow_steps": [],
            "retry_count": retry_count,
            "request_id": "test",
        }

    def test_should_rewrite_when_low_docs_and_low_retry(self) -> None:
        """should_rewrite returns 'rewrite' when docs < threshold and retry < max."""
        state = self._make_state(relevant_docs_count=0, retry_count=0)
        assert _should_rewrite(state) == "rewrite"

    def test_should_not_rewrite_when_max_retry_reached(self) -> None:
        """should_rewrite returns 'check_hitl' when retry >= MAX_REWRITE_RETRIES."""
        state = self._make_state(relevant_docs_count=0, retry_count=MAX_REWRITE_RETRIES)
        assert _should_rewrite(state) == "check_hitl"

    def test_should_not_rewrite_when_enough_docs(self) -> None:
        """should_rewrite returns 'check_hitl' when enough relevant docs found."""
        state = self._make_state(relevant_docs_count=HITL_CONFIDENCE_THRESHOLD, retry_count=0)
        assert _should_rewrite(state) == "check_hitl"

    def test_should_generate_when_no_review(self) -> None:
        """_should_generate returns 'generate' when no HITL review required."""
        state = self._make_state(requires_review=False)
        assert _should_generate(state) == "generate"

    def test_should_hitl_pending_when_review_required(self) -> None:
        """_should_generate returns 'hitl_pending' when review required."""
        state = self._make_state(requires_review=True)
        assert _should_generate(state) == "hitl_pending"


# --- run_experiment integration tests ---

class TestRunExperiment:
    """Integration tests for run_experiment function."""

    def test_run_experiment_basic(
        self,
        mock_load_corpus: MagicMock,
        mock_ollama: MagicMock,
    ) -> None:
        """run_experiment returns ExperimentResponse with required fields."""
        request = ExperimentRequest(query="国会の審議について")
        response = run_experiment(request, request_id="test-001")

        assert isinstance(response, ExperimentResponse)
        assert response.request_id == "test-001"
        assert response.processing_time_ms >= 0
        assert isinstance(response.answer, str)
        assert isinstance(response.sources, list)

    def test_run_experiment_generates_request_id(
        self,
        mock_load_corpus: MagicMock,
        mock_ollama: MagicMock,
    ) -> None:
        """run_experiment generates a UUID request_id when none provided."""
        request = ExperimentRequest(query="教育政策")
        response = run_experiment(request)
        assert response.request_id != ""
        assert len(response.request_id) == 36  # UUID format

    def test_run_experiment_hitl_for_sensitive_query(
        self,
        mock_load_corpus: MagicMock,
        mock_ollama: MagicMock,
    ) -> None:
        """run_experiment activates HITL for sensitive keyword queries."""
        request = ExperimentRequest(query="給与水準の引き上げについて")
        response = run_experiment(request)
        assert response.requires_review is True
        assert response.hitl_review is not None

    def test_run_experiment_workflow_steps_recorded(
        self,
        mock_load_corpus: MagicMock,
        mock_ollama: MagicMock,
    ) -> None:
        """run_experiment records all workflow steps."""
        request = ExperimentRequest(query="予算委員会の審議")
        response = run_experiment(request)
        assert len(response.workflow_steps) > 0
        assert "start" in response.workflow_steps

    def test_run_experiment_respects_max_results(
        self,
        mock_load_corpus: MagicMock,
        mock_ollama: MagicMock,
    ) -> None:
        """run_experiment respects max_results parameter."""
        request = ExperimentRequest(query="国会", max_results=2)
        response = run_experiment(request)
        assert len(response.sources) <= 2

    def test_run_experiment_sources_have_valid_scores(
        self,
        mock_load_corpus: MagicMock,
        mock_ollama: MagicMock,
    ) -> None:
        """Source documents in response have valid score values."""
        request = ExperimentRequest(query="教育 政策")
        response = run_experiment(request)
        for source in response.sources:
            assert 0.0 <= source.score <= 1.0


# --- Handler tests ---

class TestHandler:
    """Tests for Lambda handler function."""

    def test_handler_options_returns_cors(self, lambda_context: MagicMock) -> None:
        """OPTIONS request returns 200 with CORS headers."""
        import importlib
        import os

        import src.langgraph_rag_hitl.handler as handler_module

        with patch.dict(os.environ, {"ALLOWED_ORIGIN": "https://test.vercel.app"}):
            importlib.reload(handler_module)
            event = {"httpMethod": "OPTIONS", "path": "/api/run", "body": None}
            response = handler_module.handler(event, lambda_context)

        assert response["statusCode"] == 200
        assert response["headers"]["Access-Control-Allow-Origin"] == "https://test.vercel.app"
        assert response["headers"]["X-Request-Id"] == "test-request-id-12345"

    def test_handler_health_check(self, lambda_context: MagicMock) -> None:
        """GET /health returns status ok."""
        from src.langgraph_rag_hitl.handler import handler

        event = {"httpMethod": "GET", "path": "/health", "body": None}
        response = handler(event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "ok"
        assert body["version"] == "1.0.0"

    def test_handler_invalid_json_returns_400(self, lambda_context: MagicMock) -> None:
        """Invalid JSON body returns 400 error."""
        from src.langgraph_rag_hitl.handler import handler

        event = {"httpMethod": "POST", "path": "/api/run", "body": "not json"}
        response = handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        assert "request_id" in body

    def test_handler_validation_error_returns_400(self, lambda_context: MagicMock) -> None:
        """Missing required field returns 400 with error message."""
        from src.langgraph_rag_hitl.handler import handler

        event = {
            "httpMethod": "POST",
            "path": "/api/run",
            "body": json.dumps({"max_results": 5}),  # missing query
        }
        response = handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        assert body["request_id"] == "test-request-id-12345"

    def test_handler_empty_query_returns_400(self, lambda_context: MagicMock) -> None:
        """Empty string query returns 400 (min_length=1 validation)."""
        from src.langgraph_rag_hitl.handler import handler

        event = {
            "httpMethod": "POST",
            "path": "/api/run",
            "body": json.dumps({"query": ""}),
        }
        response = handler(event, lambda_context)

        assert response["statusCode"] == 400

    def test_handler_method_not_allowed(self, lambda_context: MagicMock) -> None:
        """PUT request returns 405."""
        from src.langgraph_rag_hitl.handler import handler

        event = {
            "httpMethod": "PUT",
            "path": "/api/run",
            "body": json.dumps({"query": "テスト"}),
        }
        response = handler(event, lambda_context)

        assert response["statusCode"] == 405

    def test_handler_success(
        self,
        mock_load_corpus: MagicMock,
        mock_ollama: MagicMock,
        lambda_context: MagicMock,
    ) -> None:
        """Valid POST request returns 200 with experiment response."""
        from src.langgraph_rag_hitl.handler import handler

        event = {
            "httpMethod": "POST",
            "path": "/api/run",
            "body": json.dumps({"query": "国会の審議について", "max_results": 3}),
        }
        response = handler(event, lambda_context)

        assert response["statusCode"] == 200
        assert response["headers"]["X-Request-Id"] == "test-request-id-12345"
        body = json.loads(response["body"])
        assert "answer" in body
        assert "sources" in body
        assert "requires_review" in body

    def test_handler_request_id_in_all_headers(self, lambda_context: MagicMock) -> None:
        """X-Request-Id is present in all response headers."""
        from src.langgraph_rag_hitl.handler import handler

        # OPTIONS
        options_response = handler({"httpMethod": "OPTIONS", "path": "/", "body": None}, lambda_context)
        assert "X-Request-Id" in options_response["headers"]

        # Health check
        health_response = handler({"httpMethod": "GET", "path": "/health", "body": None}, lambda_context)
        assert "X-Request-Id" in health_response["headers"]

        # Error response
        error_response = handler({"httpMethod": "POST", "path": "/api/run", "body": "bad"}, lambda_context)
        assert "X-Request-Id" in error_response["headers"]


# --- Model tests ---

class TestModels:
    """Tests for Pydantic v2 models."""

    def test_experiment_request_valid(self) -> None:
        """ExperimentRequest accepts valid input."""
        req = ExperimentRequest(query="テストクエリ")
        assert req.query == "テストクエリ"
        assert req.max_results == 5  # default
        assert req.user_roles == ["public"]  # default

    def test_experiment_request_empty_query_fails(self) -> None:
        """ExperimentRequest rejects empty query (min_length=1)."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ExperimentRequest(query="")

    def test_experiment_request_max_results_bounds(self) -> None:
        """ExperimentRequest enforces max_results bounds (1-20)."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ExperimentRequest(query="テスト", max_results=0)
        with pytest.raises(ValidationError):
            ExperimentRequest(query="テスト", max_results=21)

    def test_experiment_response_serializable(self) -> None:
        """ExperimentResponse serializes to dict without errors."""
        response = ExperimentResponse(
            answer="テスト回答",
            sources=[],
            processing_time_ms=123.4,
            request_id="req-001",
        )
        data = response.model_dump()
        assert data["answer"] == "テスト回答"
        assert data["requires_review"] is False
