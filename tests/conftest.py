# [DEBUG] ============================================================
# Agent   : backend_dev
# Task    : Python Lambda + Pydantic + pytest 実装
# Created : 2026-02-23T18:56:39
# Updated : 2026-02-23T18:56:39
# [/DEBUG] ===========================================================

"""pytest fixtures for LangGraph RAG HITL tests.

All fixtures mock external dependencies (Ollama) so tests pass without API keys.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# --- Sample corpus fixture ---

SAMPLE_SPEECHES: list[dict[str, Any]] = [
    {
        "speechID": "test_001",
        "issueID": "test_issue_001",
        "session": 221,
        "nameOfHouse": "参議院",
        "nameOfMeeting": "予算委員会",
        "issue": "第1号",
        "date": "2026-02-18",
        "speaker": "テスト議員A",
        "speech": "国会の審議について、予算の配分に関する議論を行いました。教育予算の拡充が重要な課題です。",
        "speechURL": "https://kokkai.ndl.go.jp/txt/test/1",
        "meetingURL": "https://kokkai.ndl.go.jp/txt/test",
        "pdfURL": None,
    },
    {
        "speechID": "test_002",
        "issueID": "test_issue_001",
        "session": 221,
        "nameOfHouse": "衆議院",
        "nameOfMeeting": "文部科学委員会",
        "issue": "第2号",
        "date": "2026-02-19",
        "speaker": "テスト議員B",
        "speech": "教育政策について議論しました。学校教育の充実と教師の待遇改善が必要です。",
        "speechURL": "https://kokkai.ndl.go.jp/txt/test/2",
        "meetingURL": "https://kokkai.ndl.go.jp/txt/test",
        "pdfURL": None,
    },
    {
        "speechID": "test_003",
        "issueID": "test_issue_002",
        "session": 221,
        "nameOfHouse": "参議院",
        "nameOfMeeting": "外交防衛委員会",
        "issue": "第3号",
        "date": "2026-02-20",
        "speaker": "テスト議員C",
        "speech": "外交政策と安全保障について審議しました。国際的な協力体制の強化が求められています。",
        "speechURL": "https://kokkai.ndl.go.jp/txt/test/3",
        "meetingURL": "https://kokkai.ndl.go.jp/txt/test",
        "pdfURL": None,
    },
    {
        "speechID": "test_004",
        "issueID": "test_issue_003",
        "session": 221,
        "nameOfHouse": "衆議院",
        "nameOfMeeting": "厚生労働委員会",
        "issue": "第4号",
        "date": "2026-02-21",
        "speaker": "テスト議員D",
        "speech": "社会保障制度の改革について議論を行いました。高齢化社会への対応が急務です。",
        "speechURL": "https://kokkai.ndl.go.jp/txt/test/4",
        "meetingURL": "https://kokkai.ndl.go.jp/txt/test",
        "pdfURL": None,
    },
    {
        "speechID": "test_005",
        "issueID": "test_issue_003",
        "session": 221,
        "nameOfHouse": "参議院",
        "nameOfMeeting": "経済産業委員会",
        "issue": "第5号",
        "date": "2026-02-22",
        "speaker": "テスト議員E",
        "speech": "経済政策について審議しました。中小企業の支援策と雇用促進が議題となりました。",
        "speechURL": "https://kokkai.ndl.go.jp/txt/test/5",
        "meetingURL": "https://kokkai.ndl.go.jp/txt/test",
        "pdfURL": None,
    },
]


@pytest.fixture
def sample_speeches() -> list[dict[str, Any]]:
    """Return sample speech records for testing.

    Returns:
        List of speech record dicts without real API calls
    """
    return SAMPLE_SPEECHES.copy()


@pytest.fixture
def mock_ollama_response() -> str:
    """Return a mock Ollama response string.

    Returns:
        Mock answer text
    """
    return "国会の審議では、予算と教育政策が主要な議題として取り上げられました。"


@pytest.fixture
def mock_ollama(mock_ollama_response: str):
    """Mock Ollama API calls to avoid network dependency.

    Patches httpx.Client.post to return a mock response.
    """
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"response": mock_ollama_response}

    with patch("httpx.Client") as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.post.return_value = mock_response
        mock_client_class.return_value = mock_client_instance
        yield mock_client_instance


@pytest.fixture
def mock_load_corpus(sample_speeches: list[dict[str, Any]]):
    """Mock _load_corpus to return sample speeches.

    Prevents file system dependency in tests.
    """
    with patch(
        "src.langgraph_rag_hitl.core._load_corpus",
        return_value=sample_speeches,
    ) as mock:
        yield mock


@pytest.fixture
def lambda_context() -> MagicMock:
    """Mock Lambda context with a fixed aws_request_id.

    Returns:
        Mock context object with aws_request_id attribute
    """
    context = MagicMock()
    context.aws_request_id = "test-request-id-12345"
    return context
