# [DEBUG] ============================================================
# Agent   : backend_dev
# Task    : Python Lambda + Pydantic + pytest 実装
# Created : 2026-02-23T18:56:39
# Updated : 2026-02-23
# [/DEBUG] ===========================================================

"""AWS Lambda handler for LangGraph RAG HITL experiment."""

import json
import os
from typing import Any

from pydantic import ValidationError

from .core import run_experiment
from .logger import get_logger
from .models import ExperimentRequest

logger = get_logger(__name__)

# NOTE: Access-Control-Allow-Origin は API Gateway の cors_configuration（variables.tf の
# cors_allowed_origins）で本番オリジンに制限すること。ここはフォールバック用ヘッダー。
# 本番では ALLOWED_ORIGIN 環境変数に具体的なオリジンを設定すること。
# 例: ALLOWED_ORIGIN=https://your-app.vercel.app
_allowed_origin = os.environ.get("ALLOWED_ORIGIN", "")

CORS_HEADERS: dict[str, str] = {
    "Access-Control-Allow-Origin": _allowed_origin,
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Request-Id",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Content-Type": "application/json",
}


def _build_response(
    status_code: int,
    body: dict[str, Any],
    request_id: str,
) -> dict[str, Any]:
    """Build a Lambda proxy response with CORS headers.

    Args:
        status_code: HTTP status code
        body: Response body dict
        request_id: Request ID for X-Request-Id header

    Returns:
        Lambda proxy response dict
    """
    headers = {**CORS_HEADERS, "X-Request-Id": request_id}
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body, ensure_ascii=False, default=str),
    }


def _build_error_response(
    status_code: int,
    message: str,
    request_id: str,
) -> dict[str, Any]:
    """Build a standardized error response.

    Args:
        status_code: HTTP status code (400 for validation, 500 for internal)
        message: Human-readable error message
        request_id: Request ID for tracing

    Returns:
        Lambda proxy error response dict
    """
    return _build_response(
        status_code=status_code,
        body={"error": message, "request_id": request_id},
        request_id=request_id,
    )


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda handler for the RAG HITL experiment.

    Handles:
    - OPTIONS: CORS preflight
    - POST /api/run: Run the RAG HITL experiment
    - Other: 404

    Args:
        event: Lambda event dict (API Gateway proxy format)
        context: Lambda context object (must have aws_request_id)

    Returns:
        Lambda proxy response dict with statusCode/body/headers
    """
    request_id: str = getattr(context, "aws_request_id", "unknown")
    http_method: str = event.get("httpMethod", "POST").upper()
    path: str = event.get("path", "/api/run")

    logger.info(
        "request_received",
        extra={
            "request_id": request_id,
            "method": http_method,
            "path": path,
        },
    )

    # Handle CORS preflight
    if http_method == "OPTIONS":
        return _build_response(200, {}, request_id)

    # Health check
    if path == "/health" and http_method == "GET":
        return _build_response(200, {"status": "ok", "version": "1.0.0"}, request_id)

    # Only accept POST /api/run
    if http_method != "POST":
        return _build_error_response(405, "Method not allowed", request_id)

    # Parse and validate request body
    raw_body = event.get("body") or "{}"
    try:
        body_dict = json.loads(raw_body)
    except json.JSONDecodeError as e:
        logger.warning(
            "invalid_json",
            extra={"request_id": request_id, "error": str(e)},
        )
        return _build_error_response(400, f"Invalid JSON: {e}", request_id)

    try:
        request = ExperimentRequest(**body_dict)
    except ValidationError as e:
        logger.warning(
            "validation_error",
            extra={"request_id": request_id, "errors": e.errors()},
        )
        errors = [f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in e.errors()]
        return _build_error_response(400, f"Validation error: {'; '.join(errors)}", request_id)

    # Run experiment
    try:
        response = run_experiment(request, request_id=request_id)
        return _build_response(200, response.model_dump(), request_id)
    except Exception as e:
        logger.error(
            "internal_error",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True,
        )
        return _build_error_response(500, "Internal server error", request_id)
