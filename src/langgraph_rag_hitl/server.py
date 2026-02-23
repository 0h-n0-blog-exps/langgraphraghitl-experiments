# [DEBUG] ============================================================
# Agent   : backend_dev
# Task    : Python Lambda + Pydantic + pytest 実装
# Created : 2026-02-23T18:56:39
# Updated : 2026-02-23
# [/DEBUG] ===========================================================

"""FastAPI local development server for docker compose."""

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .core import run_experiment
from .logger import get_logger
from .models import ExperimentRequest, ExperimentResponse

logger = get_logger(__name__)

# 本番では ALLOWED_ORIGINS 環境変数にカンマ区切りでオリジンを指定すること
# 例: ALLOWED_ORIGINS=https://your-app.vercel.app
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS: list[str] = [o.strip() for o in _raw_origins.split(",")]

app = FastAPI(
    title="LangGraph RAG HITL API",
    description="Multi-source RAG with Human-in-the-Loop for 国会議事録 search",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Status and version dict
    """
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/run", response_model=ExperimentResponse)
async def run(request: ExperimentRequest) -> ExperimentResponse:
    """Run the RAG HITL experiment.

    Args:
        request: ExperimentRequest with query and parameters

    Returns:
        ExperimentResponse with answer and sources

    Raises:
        HTTPException: 500 on internal error
    """
    try:
        return run_experiment(request)
    except Exception as e:
        logger.error("server_error", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e
