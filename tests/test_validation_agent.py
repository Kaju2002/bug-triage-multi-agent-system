# tests/test_validation_agent.py

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Make project importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.validation_agent import validation_node


# ── Sample state ───────────────────────────────────────────────

SAMPLE_STATE = {
    "bug_analysis": {
        "root_cause": "Null pointer in login",
        "affected_components": ["src/auth.py::login"],
        "severity": "critical",
        "category": "crash",
    },
    "fix_suggestion": {
        "fix_description": "Add null check",
        "code_patch": "if password is None: return error",
        "confidence": "high",
    },
    "logs": [],
}


def _mock_llm_response():
    mock = MagicMock()
    response = MagicMock()
    response.content = """
    {
        "is_valid": true,
        "issues": [],
        "improvement_suggestions": [],
        "validation_confidence": "high"
    }
    """
    mock.invoke.return_value = response
    return mock


# ── TEST 1 ───────────────────────────────────────────

@patch("agents.validation_agent.get_ollama_model")
def test_validation_success(MockLLM):
    MockLLM.return_value = _mock_llm_response()

    result = validation_node(dict(SAMPLE_STATE))

    assert result["is_valid"] is True
    assert "validation_result" in result


# ── TEST 2 ───────────────────────────────────────────

@patch("agents.validation_agent.get_ollama_model")
def test_missing_keys_fails(MockLLM):
    MockLLM.return_value = _mock_llm_response()

    bad_state = {
        "bug_analysis": {},
        "fix_suggestion": {},
        "logs": [],
    }

    result = validation_node(bad_state)

    assert result["is_valid"] is False


# ── TEST 3 ───────────────────────────────────────────

@patch("agents.validation_agent.get_ollama_model")
def test_logs_added(MockLLM):
    MockLLM.return_value = _mock_llm_response()

    result = validation_node(dict(SAMPLE_STATE))

    assert len(result["logs"]) > 0
    assert result["logs"][-1]["agent"] == "ValidationAgent"