# [DEBUG] ============================================================
# Agent   : backend_dev
# Task    : Python Lambda + Pydantic + pytest 実装
# Created : 2026-02-23T18:56:39
# Updated : 2026-02-23T18:56:39
# [/DEBUG] ===========================================================

"""Pydantic v2 models for LangGraph RAG HITL experiment."""

from typing import Literal

from pydantic import BaseModel, Field


class ExperimentRequest(BaseModel):
    """Request model for RAG HITL experiment."""

    query: str = Field(..., min_length=1, max_length=500, description="Search query in Japanese")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum number of documents to retrieve")
    user_roles: list[str] = Field(
        default_factory=lambda: ["public"],
        description="User roles for permission-aware retrieval",
    )


class SourceDocument(BaseModel):
    """A source document retrieved from the corpus."""

    speech_id: str = Field(..., description="Unique speech identifier")
    speaker: str = Field(..., description="Speaker name")
    date: str = Field(..., description="Date of the speech")
    content: str = Field(..., description="Speech content")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")
    house: str = Field(default="", description="Name of house (衆議院/参議院)")
    meeting: str = Field(default="", description="Meeting name")


class GradedDocument(BaseModel):
    """A document with relevance grading."""

    document: SourceDocument
    is_relevant: bool = Field(..., description="Whether the document is relevant to the query")
    grade_reason: str = Field(default="", description="Reason for grading decision")


class HITLReviewRequest(BaseModel):
    """Request for Human-in-the-Loop review."""

    reason: Literal["low_confidence", "sensitive_topic"] = Field(
        ..., description="Reason for HITL activation"
    )
    query: str = Field(..., description="Original query")
    relevant_doc_count: int = Field(..., description="Number of relevant documents found")
    sensitive_keywords: list[str] = Field(
        default_factory=list, description="Sensitive keywords detected"
    )


class ExperimentResponse(BaseModel):
    """Response model for RAG HITL experiment."""

    answer: str = Field(..., description="Generated answer")
    sources: list[SourceDocument] = Field(default_factory=list, description="Source documents used")
    requires_review: bool = Field(default=False, description="Whether HITL review is required")
    hitl_review: HITLReviewRequest | None = Field(
        default=None, description="HITL review details if required"
    )
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    request_id: str = Field(..., description="Request identifier")
    workflow_steps: list[str] = Field(
        default_factory=list, description="Steps executed in the LangGraph workflow"
    )
