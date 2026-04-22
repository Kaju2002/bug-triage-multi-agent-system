# tests/test_fix_generation.py
# Member 3 — Fix Generation Agent — Full Test Suite (10+ test cases)
# Run with: pytest tests/test_fix_generation.py -v

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Make project root importable ─────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.fix_suggester_tool import suggest_fix
from agents.fix_generation_agent import (
    _clean_json_response,
    _passes_quality_filter,
    _score_to_level,
    fix_generation_node,
)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Unit tests for suggest_fix() (tools/fix_suggester_tool.py)
# ═════════════════════════════════════════════════════════════════════════════

class TestSuggestFix:
    """Unit tests for the keyword-based rule fix suggester."""

    # ── Test 1 ────────────────────────────────────────────────────────────
    def test_null_pointer_root_cause_returns_null_check_strategy(self):
        """'null pointer' in root cause must return fix_strategy = null_check."""
        result = suggest_fix(
            root_cause="login() does not guard against null pointer in the password field",
            language="python",
            severity="critical",
        )
        assert result["fix_strategy"] == "null_check", (
            f"Expected 'null_check', got {result['fix_strategy']!r}"
        )

    # ── Test 2 ────────────────────────────────────────────────────────────
    def test_race_condition_returns_synchronization_strategy(self):
        """'race condition' in root cause must return fix_strategy = synchronization."""
        result = suggest_fix(
            root_cause="Shared counter is updated by multiple threads without a race condition guard",
            language="python",
            severity="high",
        )
        assert result["fix_strategy"] == "synchronization", (
            f"Expected 'synchronization', got {result['fix_strategy']!r}"
        )

    # ── Test 3 ────────────────────────────────────────────────────────────
    def test_sql_injection_returns_input_validation_strategy(self):
        """'injection' in root cause must return fix_strategy = input_validation."""
        result = suggest_fix(
            root_cause="User input is concatenated directly into the SQL query without sanitization (injection risk)",
            language="python",
            severity="critical",
        )
        assert result["fix_strategy"] == "input_validation", (
            f"Expected 'input_validation', got {result['fix_strategy']!r}"
        )

    # ── Test 4 ────────────────────────────────────────────────────────────
    def test_memory_leak_returns_resource_management_strategy(self):
        """'memory leak' in root cause must return fix_strategy = resource_management."""
        result = suggest_fix(
            root_cause="File handles are opened but never closed, causing a memory leak",
            language="python",
            severity="high",
        )
        assert result["fix_strategy"] == "resource_management", (
            f"Expected 'resource_management', got {result['fix_strategy']!r}"
        )

    # ── Test 5 ────────────────────────────────────────────────────────────
    def test_unknown_root_cause_returns_code_review_strategy(self):
        """A root cause with no recognisable keywords must fall back to code_review."""
        result = suggest_fix(
            root_cause="The feature behaves inconsistently under unknown conditions",
            language="python",
            severity="medium",
        )
        assert result["fix_strategy"] == "code_review", (
            f"Expected 'code_review', got {result['fix_strategy']!r}"
        )

    # ── Test 6 ────────────────────────────────────────────────────────────
    def test_result_contains_required_keys(self):
        """suggest_fix must always return a dict with the four required keys."""
        result = suggest_fix(
            root_cause="An off by one error causes the loop to skip the last element",
            language="python",
            severity="medium",
        )
        for key in ("fix_strategy", "code_pattern", "references", "language", "severity"):
            assert key in result, f"Missing key in suggest_fix result: {key!r}"

    # ── Test 7 ────────────────────────────────────────────────────────────
    def test_references_is_a_list(self):
        """references must always be a non-empty list of strings."""
        result = suggest_fix(
            root_cause="Null pointer when user object is not found",
            language="python",
            severity="high",
        )
        assert isinstance(result["references"], list), "references must be a list"
        assert len(result["references"]) > 0, "references must not be empty"

    # ── Test 8 ────────────────────────────────────────────────────────────
    def test_empty_root_cause_raises_value_error(self):
        """Empty root_cause must raise ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            suggest_fix(root_cause="", language="python", severity="low")

    # ── Test 9 ────────────────────────────────────────────────────────────
    def test_non_string_root_cause_raises_type_error(self):
        """Non-string root_cause must raise TypeError."""
        with pytest.raises(TypeError):
            suggest_fix(root_cause=42, language="python", severity="low")  # type: ignore[arg-type]

    # ── Test 10 ───────────────────────────────────────────────────────────
    def test_boundary_check_strategy_for_off_by_one(self):
        """'off by one' must map to boundary_check strategy."""
        result = suggest_fix(
            root_cause="Off by one error in the loop boundary causes the last item to be skipped",
            language="python",
            severity="medium",
        )
        assert result["fix_strategy"] == "boundary_check"

    # ── Test 11 ───────────────────────────────────────────────────────────
    def test_auth_hardening_for_authentication_root_cause(self):
        """'authentication' in root cause must return auth_hardening strategy."""
        result = suggest_fix(
            root_cause="Missing authentication check allows unauthenticated access to admin route",
            language="python",
            severity="critical",
        )
        assert result["fix_strategy"] == "auth_hardening"

    # ── Test 12 ───────────────────────────────────────────────────────────
    def test_language_and_severity_preserved_in_result(self):
        """language and severity values passed in must be reflected in the result."""
        result = suggest_fix(
            root_cause="Null pointer dereference on missing config value",
            language="java",
            severity="critical",
        )
        assert result["language"]  == "java"
        assert result["severity"]  == "critical"

    # ── Test 13 ───────────────────────────────────────────────────────────
    def test_code_pattern_is_non_empty_string(self):
        """code_pattern must be a non-empty string for every known strategy."""
        result = suggest_fix(
            root_cause="Uncaught exception propagates silently",
            language="python",
            severity="high",
        )
        assert isinstance(result["code_pattern"], str)
        assert len(result["code_pattern"].strip()) > 0


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Unit tests for helpers in fix_generation_agent.py
# ═════════════════════════════════════════════════════════════════════════════

class TestCleanJsonResponse:
    """Tests for the _clean_json_response helper."""

    def test_strips_json_fence(self):
        raw = "```json\n{\"key\": \"value\"}\n```"
        assert _clean_json_response(raw) == '{"key": "value"}'

    def test_strips_plain_fence(self):
        raw = "```\n{\"key\": 1}\n```"
        assert _clean_json_response(raw) == '{"key": 1}'

    def test_no_fence_unchanged(self):
        raw = '{"key": "value"}'
        assert _clean_json_response(raw) == raw

    def test_whitespace_trimmed(self):
        raw = "   {\"a\": 1}   "
        assert _clean_json_response(raw) == '{"a": 1}'


class TestPassesQualityFilter:
    """Tests for the _passes_quality_filter helper."""

    def _valid(self) -> dict:
        return {
            "fix_description":  "Add a null check before accessing the password field.",
            "code_snippet":     "if password is None:\n    raise ValueError('password required')",
            "confidence_score": 0.85,
        }

    def test_valid_result_passes(self):
        assert _passes_quality_filter(self._valid()) is True

    def test_short_description_fails(self):
        d = self._valid()
        d["fix_description"] = "Too short"
        assert _passes_quality_filter(d) is False

    def test_short_snippet_fails(self):
        d = self._valid()
        d["code_snippet"] = "pass"
        assert _passes_quality_filter(d) is False

    def test_refusal_phrase_in_description_fails(self):
        d = self._valid()
        d["fix_description"] = "I cannot provide a fix for this specific case here."
        assert _passes_quality_filter(d) is False

    def test_refusal_phrase_in_snippet_fails(self):
        d = self._valid()
        d["code_snippet"] = "As an AI I am unable to generate this code snippet safely."
        assert _passes_quality_filter(d) is False

    def test_out_of_range_confidence_fails(self):
        d = self._valid()
        d["confidence_score"] = 1.5
        assert _passes_quality_filter(d) is False

    def test_non_numeric_confidence_fails(self):
        d = self._valid()
        d["confidence_score"] = "high"
        assert _passes_quality_filter(d) is False

    def test_confidence_at_boundaries(self):
        d = self._valid()
        d["confidence_score"] = 0.0
        assert _passes_quality_filter(d) is True
        d["confidence_score"] = 1.0
        assert _passes_quality_filter(d) is True


class TestScoreToLevel:
    """Tests for the _score_to_level helper."""

    def test_high_threshold(self):
        assert _score_to_level(0.7)  == "high"
        assert _score_to_level(0.95) == "high"
        assert _score_to_level(1.0)  == "high"

    def test_medium_threshold(self):
        assert _score_to_level(0.4)  == "medium"
        assert _score_to_level(0.55) == "medium"
        assert _score_to_level(0.69) == "medium"

    def test_low_threshold(self):
        assert _score_to_level(0.0)  == "low"
        assert _score_to_level(0.2)  == "low"
        assert _score_to_level(0.39) == "low"


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Integration tests for fix_generation_node() with mocked LLM
# ═════════════════════════════════════════════════════════════════════════════

# Sample state that simulates Agent 2's output
SAMPLE_STATE = {
    "raw_bug_report": (
        "Login crashes on empty password\n"
        "When a user submits the login form with an empty password field, "
        "the server crashes with a NullPointerException in the auth module."
    ),
    "bug_analysis": {
        "root_cause": "login() does not guard against null pointer when password is empty",
        "affected_components": ["src/auth.py::login", "src/models.py::User"],
        "severity": "critical",
        "category": "crash",
        "reproduction_steps": ["Go to /login", "Leave password blank", "Click Submit"],
        "analysis_confidence": "high",
    },
    "code_map": {
        "src/auth.py":   ["login", "logout", "hash_password"],
        "src/models.py": ["User", "Session"],
    },
    "logs": [],
}

VALID_LLM_RESPONSE = {
    "fix_description": (
        "Add a null/empty guard at the start of login() so that an empty password "
        "raises a clear ValueError before any hashing or DB lookup occurs."
    ),
    "code_snippet": (
        "def login(username: str, password: str):\n"
        "    if not password:\n"
        "        raise ValueError('Password must not be empty')\n"
        "    # ... rest of login logic"
    ),
    "confidence_score": 0.9,
}


def _make_llm_mock(response_dict: dict) -> MagicMock:
    """Return a mock that replaces get_ollama_model().invoke()."""
    mock_instance          = MagicMock()
    mock_response          = MagicMock()
    mock_response.content  = json.dumps(response_dict)
    mock_instance.invoke.return_value = mock_response
    return mock_instance


class TestFixGenerationNode:
    """Integration tests for the LangGraph node with mocked Ollama."""

    # ── Test 1 ────────────────────────────────────────────────────────────
    @patch("agents.fix_generation_agent.get_ollama_model")
    def test_node_returns_all_required_state_keys(self, MockGetOllama):
        """Agent output must contain proposed_fix, fix_suggestion, and logs."""
        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)

        result = fix_generation_node(dict(SAMPLE_STATE))

        assert "proposed_fix"   in result, "proposed_fix key missing from state"
        assert "fix_suggestion" in result, "fix_suggestion key missing from state"
        assert "logs"           in result, "logs key missing from state"

    # ── Test 2 ────────────────────────────────────────────────────────────
    @patch("agents.fix_generation_agent.get_ollama_model")
    def test_proposed_fix_contains_all_required_keys(self, MockGetOllama):
        """proposed_fix must contain all six schema keys."""
        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)

        result = fix_generation_node(dict(SAMPLE_STATE))
        proposed_fix = result["proposed_fix"]

        for key in ("fix_description", "code_snippet", "fix_strategy",
                    "confidence_score", "references", "llm_used"):
            assert key in proposed_fix, f"Missing key in proposed_fix: {key!r}"

    # ── Test 3 ────────────────────────────────────────────────────────────
    @patch("agents.fix_generation_agent.get_ollama_model")
    def test_confidence_score_is_float_in_range(self, MockGetOllama):
        """confidence_score in proposed_fix must be a float in [0.0, 1.0]."""
        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)

        result = fix_generation_node(dict(SAMPLE_STATE))
        score  = result["proposed_fix"]["confidence_score"]

        assert isinstance(score, float), f"confidence_score must be float, got {type(score)}"
        assert 0.0 <= score <= 1.0, f"confidence_score out of range: {score}"

    # ── Test 4 ────────────────────────────────────────────────────────────
    @patch("agents.fix_generation_agent.get_ollama_model")
    def test_valid_llm_response_sets_llm_used_true(self, MockGetOllama):
        """When the LLM response passes the quality filter, llm_used must be True."""
        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)

        result = fix_generation_node(dict(SAMPLE_STATE))

        assert result["proposed_fix"]["llm_used"] is True

    # ── Test 5 ────────────────────────────────────────────────────────────
    @patch("agents.fix_generation_agent.get_ollama_model")
    def test_garbage_llm_response_activates_fallback(self, MockGetOllama):
        """If LLM returns unparseable text, llm_used must be False (rule-based fallback)."""
        mock_instance          = MagicMock()
        mock_response          = MagicMock()
        mock_response.content  = "This is not JSON at all! ¯\\_(ツ)_/¯"
        mock_instance.invoke.return_value = mock_response
        MockGetOllama.return_value = mock_instance

        result = fix_generation_node(dict(SAMPLE_STATE))   # must NOT raise

        assert result["proposed_fix"]["llm_used"] is False
        assert "proposed_fix" in result

    # ── Test 6 ────────────────────────────────────────────────────────────
    @patch("agents.fix_generation_agent.get_ollama_model")
    def test_refusal_phrase_activates_fallback(self, MockGetOllama):
        """If LLM response contains a refusal phrase, llm_used must be False."""
        refusal_response = {
            "fix_description": "I cannot provide a specific fix for this security issue.",
            "code_snippet":    "As an AI I am unable to generate exploit fixes safely here.",
            "confidence_score": 0.1,
        }
        MockGetOllama.return_value = _make_llm_mock(refusal_response)

        result = fix_generation_node(dict(SAMPLE_STATE))

        assert result["proposed_fix"]["llm_used"] is False

    # ── Test 7 ────────────────────────────────────────────────────────────
    @patch("agents.fix_generation_agent.get_ollama_model")
    def test_fix_suggestion_has_agent4_compatible_keys(self, MockGetOllama):
        """fix_suggestion must have fix_description, code_patch, and confidence."""
        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)

        result         = fix_generation_node(dict(SAMPLE_STATE))
        fix_suggestion = result["fix_suggestion"]

        assert "fix_description" in fix_suggestion, "fix_description missing from fix_suggestion"
        assert "code_patch"      in fix_suggestion, "code_patch missing from fix_suggestion"
        assert "confidence"      in fix_suggestion, "confidence missing from fix_suggestion"

    # ── Test 8 ────────────────────────────────────────────────────────────
    @patch("agents.fix_generation_agent.get_ollama_model")
    def test_fix_suggestion_confidence_is_level_string(self, MockGetOllama):
        """fix_suggestion['confidence'] must be 'high', 'medium', or 'low'."""
        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)

        result     = fix_generation_node(dict(SAMPLE_STATE))
        confidence = result["fix_suggestion"]["confidence"]

        assert confidence in ("high", "medium", "low"), (
            f"Expected high/medium/low, got {confidence!r}"
        )

    # ── Test 9 ────────────────────────────────────────────────────────────
    @patch("agents.fix_generation_agent.get_ollama_model")
    def test_missing_state_keys_handled_gracefully(self, MockGetOllama):
        """Agent must not crash when bug_analysis or code_map are absent."""
        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)

        minimal_state = {"logs": []}
        result = fix_generation_node(minimal_state)   # must NOT raise

        assert "proposed_fix"   in result
        assert "fix_suggestion" in result

    # ── Test 10 ───────────────────────────────────────────────────────────
    @patch("agents.fix_generation_agent.get_ollama_model")
    def test_log_entry_appended_with_correct_agent_name(self, MockGetOllama):
        """A log entry for FixGenerationAgent must be appended to state['logs']."""
        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)

        result = fix_generation_node(dict(SAMPLE_STATE))

        agent_logs = [
            e for e in result["logs"]
            if e.get("agent") == "FixGenerationAgent"
        ]
        assert len(agent_logs) >= 1, "No log entry found for FixGenerationAgent"
        assert agent_logs[-1]["success"] is True

    # ── Test 11 ───────────────────────────────────────────────────────────
    @patch("agents.fix_generation_agent.get_ollama_model")
    def test_fix_strategy_comes_from_rule_based_tool(self, MockGetOllama):
        """fix_strategy in proposed_fix must always originate from the rule-based tool."""
        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)

        result        = fix_generation_node(dict(SAMPLE_STATE))
        fix_strategy  = result["proposed_fix"]["fix_strategy"]

        valid_strategies = {
            "null_check", "boundary_check", "synchronization",
            "resource_management", "input_validation", "auth_hardening",
            "timeout_handling", "error_handling", "code_review",
        }
        assert fix_strategy in valid_strategies, (
            f"fix_strategy {fix_strategy!r} is not a known rule-based strategy"
        )

    # ── Test 12 ───────────────────────────────────────────────────────────
    @patch("agents.fix_generation_agent.get_ollama_model")
    def test_references_is_list_in_proposed_fix(self, MockGetOllama):
        """references in proposed_fix must always be a list."""
        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)

        result = fix_generation_node(dict(SAMPLE_STATE))

        assert isinstance(result["proposed_fix"]["references"], list)

    # ── Test 13 ───────────────────────────────────────────────────────────
    @patch("agents.fix_generation_agent.get_ollama_model")
    def test_fallback_fix_description_is_non_empty(self, MockGetOllama):
        """Even in fallback mode, fix_description must be a non-empty string."""
        mock_instance          = MagicMock()
        mock_response          = MagicMock()
        mock_response.content  = "INVALID JSON"
        mock_instance.invoke.return_value = mock_response
        MockGetOllama.return_value = mock_instance

        result       = fix_generation_node(dict(SAMPLE_STATE))
        fix_desc     = result["proposed_fix"]["fix_description"]

        assert isinstance(fix_desc, str) and len(fix_desc.strip()) > 0

    # ── Test 14 ───────────────────────────────────────────────────────────
    @patch("agents.fix_generation_agent.get_ollama_model")
    def test_low_confidence_llm_still_accepted_if_above_filter(self, MockGetOllama):
        """A low but valid confidence score (0.31) must still pass the filter."""
        low_conf_response = {
            "fix_description": (
                "Wrap the password access in a conditional guard to prevent crash."
            ),
            "code_snippet": (
                "if password is None or password == '':\n"
                "    return {'error': 'Password required'}, 400"
            ),
            "confidence_score": 0.31,
        }
        MockGetOllama.return_value = _make_llm_mock(low_conf_response)

        result = fix_generation_node(dict(SAMPLE_STATE))

        assert result["proposed_fix"]["llm_used"] is True
        assert result["proposed_fix"]["confidence_score"] == pytest.approx(0.31)
