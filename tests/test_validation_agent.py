# tests/test_validation_agent.py
# Member 4 — Validation Agent Test Suite (10+ tests)
# Run with: pytest tests/test_validation_agent.py -v

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Make project root importable ─────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.validation_agent import validation_node


# ═════════════════════════════════════════════════════════════════════════════
# SAMPLE STATE
# ═════════════════════════════════════════════════════════════════════════════

SAMPLE_STATE = {
    "bug_analysis": {
        "root_cause": "Null pointer when password is empty",
        "severity": "high",
        "affected_components": ["auth.py::login"],
        "category": "logic",
    },
    "fix_suggestion": {
        "fix_description": "Add null check before accessing password",
        "code_patch": "if password is None: return error",
        "confidence": "high",
    },
    "logs": [],
}


def _mock_llm_response(data: dict):
    mock = MagicMock()
    response = MagicMock()
    response.content = json.dumps(data)
    mock.invoke.return_value = response
    return mock


VALID_RESPONSE = {
    "is_valid": True,
    "issues": [],
    "improvement_suggestions": [],
    "validation_confidence": "high",
}


# ═════════════════════════════════════════════════════════════════════════════
# TEST CASES
# ═════════════════════════════════════════════════════════════════════════════

class TestValidationAgent:

    # ── 1. Basic success test ───────────────────────────────────────────
    @patch("agents.validation_agent.get_ollama_model")
    def test_validation_success(self, MockLLM):
        MockLLM.return_value = _mock_llm_response(VALID_RESPONSE)

        result = validation_node(dict(SAMPLE_STATE))

        assert "validation_result" in result
        assert result["is_valid"] is True

    # ── 2. Missing keys should not crash ────────────────────────────────
    @patch("agents.validation_agent.get_ollama_model")
    def test_missing_keys_handled(self, MockLLM):
        MockLLM.return_value = _mock_llm_response(VALID_RESPONSE)

        state = {"logs": []}  # minimal state
        result = validation_node(state)

        assert "validation_result" in result

    # ── 3. Invalid JSON from LLM (fallback test) ────────────────────────
    @patch("agents.validation_agent.get_ollama_model")
    def test_invalid_llm_response(self, MockLLM):
        mock = MagicMock()
        response = MagicMock()
        response.content = "NOT JSON"
        mock.invoke.return_value = response
        MockLLM.return_value = mock

        result = validation_node(dict(SAMPLE_STATE))

        assert result["is_valid"] is False
        assert "Invalid LLM response" in result["validation_result"]["issues"]

    # ── 4. Structure validation failure forces invalid ──────────────────
    @patch("agents.validation_agent.get_ollama_model")
    @patch("agents.validation_agent.validate_report_structure")
    def test_structure_failure(self, MockTool, MockLLM):
        MockLLM.return_value = _mock_llm_response(VALID_RESPONSE)
        MockTool.return_value = {"valid": False, "errors": ["Missing field"]}

        result = validation_node(dict(SAMPLE_STATE))

        assert result["is_valid"] is False
        assert "Missing field" in result["validation_result"]["issues"]

    # ── 5. Logging is added correctly ───────────────────────────────────
    @patch("agents.validation_agent.get_ollama_model")
    def test_logs_added(self, MockLLM):
        MockLLM.return_value = _mock_llm_response(VALID_RESPONSE)

        result = validation_node(dict(SAMPLE_STATE))

        assert len(result["logs"]) > 0
        assert result["logs"][-1]["agent"] == "ValidationAgent"

    # ── 6. Validation confidence exists ─────────────────────────────────
    @patch("agents.validation_agent.get_ollama_model")
    def test_validation_confidence_present(self, MockLLM):
        MockLLM.return_value = _mock_llm_response(VALID_RESPONSE)

        result = validation_node(dict(SAMPLE_STATE))

        assert "validation_confidence" in result["validation_result"]

    # ── 7. Invalid fix should be rejected ───────────────────────────────
    @patch("agents.validation_agent.get_ollama_model")
    def test_invalid_fix_rejected(self, MockLLM):
        bad_response = {
            "is_valid": False,
            "issues": ["Fix does not address root cause"],
            "improvement_suggestions": ["Add proper validation"],
            "validation_confidence": "high",
        }

        MockLLM.return_value = _mock_llm_response(bad_response)

        result = validation_node(dict(SAMPLE_STATE))

        assert result["is_valid"] is False

    # ── 8. Security issue detection ─────────────────────────────────────
    @patch("agents.validation_agent.get_ollama_model")
    def test_security_issue_detected(self, MockLLM):
        security_response = {
            "is_valid": False,
            "issues": ["SQL injection risk"],
            "improvement_suggestions": ["Use parameterized queries"],
            "validation_confidence": "high",
        }

        MockLLM.return_value = _mock_llm_response(security_response)

        result = validation_node(dict(SAMPLE_STATE))

        assert result["is_valid"] is False
        assert "SQL injection risk" in result["validation_result"]["issues"]

    # ── 9. Empty bug_analysis handled ───────────────────────────────────
    @patch("agents.validation_agent.get_ollama_model")
    def test_empty_bug_analysis(self, MockLLM):
        MockLLM.return_value = _mock_llm_response(VALID_RESPONSE)

        state = {
            "bug_analysis": {},
            "fix_suggestion": {
                "fix_description": "fix",
                "code_patch": "patch",
                "confidence": "low",
            },
            "logs": [],
        }

        result = validation_node(state)

        assert "validation_result" in result

    # ── 10. Empty fix suggestion handled ────────────────────────────────
    @patch("agents.validation_agent.get_ollama_model")
    def test_empty_fix_suggestion(self, MockLLM):
        MockLLM.return_value = _mock_llm_response(VALID_RESPONSE)

        state = {
            "bug_analysis": SAMPLE_STATE["bug_analysis"],
            "fix_suggestion": {
                "fix_description": "",
                "code_patch": "",
                "confidence": "",
            },
            "logs": [],
        }

        result = validation_node(state)

        assert "validation_result" in result

    # ── 11. Output keys always exist ────────────────────────────────────
    @patch("agents.validation_agent.get_ollama_model")
    def test_output_keys_exist(self, MockLLM):
        MockLLM.return_value = _mock_llm_response(VALID_RESPONSE)

        result = validation_node(dict(SAMPLE_STATE))

        assert "validation_result" in result
        assert "is_valid" in result

    # ── 12. Issues list is always a list ─────────────────────────────────
    @patch("agents.validation_agent.get_ollama_model")
    def test_issues_is_list(self, MockLLM):
        MockLLM.return_value = _mock_llm_response(VALID_RESPONSE)

        result = validation_node(dict(SAMPLE_STATE))

        assert isinstance(result["validation_result"]["issues"], list)
