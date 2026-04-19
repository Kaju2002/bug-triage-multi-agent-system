# tests/test_bug_analysis.py
# Member 2 — Bug Analysis Agent — Full Test Suite (7+ test cases)
# Run with: pytest tests/test_bug_analysis.py -v

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Make project root importable ─────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.bug_classifier_tool import classify_bug
from agents.bug_analysis_agent import (
    _clean_json_response,
    _validate_analysis,
    bug_analysis_node,
    REQUIRED_KEYS,
    VALID_SEVERITIES,
    VALID_CATEGORIES,
)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Unit tests for classify_bug() (tools/bug_classifier_tool.py)
# ═════════════════════════════════════════════════════════════════════════════

class TestClassifyBug:
    """Unit tests for the keyword-based rule classifier."""

    # ── Test 1 ────────────────────────────────────────────────────────────
    def test_data_loss_returns_critical_severity(self):
        """'data loss' in description must return rule_severity = critical."""
        result = classify_bug(
            title="Database wipe",
            description="User data loss occurred after the migration script ran.",
        )
        assert result["rule_severity"] == "critical", (
            f"Expected 'critical', got {result['rule_severity']!r}"
        )

    # ── Test 2 ────────────────────────────────────────────────────────────
    def test_cosmetic_bug_returns_low_severity_and_ui_category(self):
        """'button colour wrong' must return severity=low and category=ui."""
        result = classify_bug(
            title="Button colour wrong",
            description="The submit button background colour does not match the design.",
        )
        assert result["rule_severity"] == "low",  (
            f"Expected 'low', got {result['rule_severity']!r}"
        )
        assert result["rule_category"] == "ui", (
            f"Expected 'ui', got {result['rule_category']!r}"
        )

    # ── Test 3 ────────────────────────────────────────────────────────────
    def test_empty_title_and_description_raises_value_error(self):
        """Empty title AND empty description must raise ValueError."""
        with pytest.raises(ValueError, match="cannot both be empty"):
            classify_bug(title="", description="")

    # ── Test 4 ────────────────────────────────────────────────────────────
    def test_empty_title_with_valid_description_does_not_raise(self):
        """Empty title is fine as long as description is non-empty."""
        result = classify_bug(title="", description="The app crashes on startup.")
        assert result["rule_severity"] in VALID_SEVERITIES

    # ── Test 5 ────────────────────────────────────────────────────────────
    def test_security_keyword_returns_critical(self):
        """'authentication' in bug text must be classified as critical."""
        result = classify_bug(
            title="Auth bypass",
            description="Unauthorised users can access admin endpoints without authentication.",
        )
        assert result["rule_severity"] == "critical"

    # ── Test 6 ────────────────────────────────────────────────────────────
    def test_performance_keyword_returns_performance_category(self):
        """'slow' and 'timeout' must map to performance category."""
        result = classify_bug(
            title="API is slow",
            description="The endpoint times out after 30 seconds under normal load.",
        )
        assert result["rule_category"] == "performance"

    # ── Test 7 ────────────────────────────────────────────────────────────
    def test_error_message_influences_classification(self):
        """error_message parameter must be included in combined text analysis."""
        result = classify_bug(
            title="App crashes",
            description="The app sometimes stops.",
            error_message="Segmentation fault (core dumped)",
        )
        assert result["rule_severity"] == "critical"
        assert result["rule_category"] == "crash"

    # ── Test 8 ────────────────────────────────────────────────────────────
    def test_matched_terms_is_a_list(self):
        """matched_terms must always be a list (even if empty)."""
        result = classify_bug(title="Some bug", description="xyz abc")
        assert isinstance(result["matched_terms"], list)

    # ── Test 9 ────────────────────────────────────────────────────────────
    def test_text_length_matches_combined_input(self):
        """text_length must equal len of combined title+description+error string."""
        title, desc, err = "Bug", "Something broke", "Traceback error"
        result = classify_bug(title=title, description=desc, error_message=err)
        expected_len = len(f"{title} {desc} {err}".lower())
        assert result["text_length"] == expected_len

    # ── Test 10 ───────────────────────────────────────────────────────────
    def test_network_keyword_returns_integration_category(self):
        """'api' keyword must map to integration category."""
        result = classify_bug(
            title="API 404",
            description="The third-party API connection returns 404 on all requests.",
        )
        assert result["rule_category"] == "integration"


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Unit tests for helpers in bug_analysis_agent.py
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


class TestValidateAnalysis:
    """Tests for the _validate_analysis helper."""

    def _valid_analysis(self) -> dict:
        return {
            "root_cause":           "Null pointer in login()",
            "affected_components":  ["src/auth.py"],
            "severity":             "high",
            "category":             "crash",
            "reproduction_steps":   ["Step 1", "Step 2"],
            "analysis_confidence":  "high",
        }

    def test_valid_analysis_returns_no_errors(self):
        assert _validate_analysis(self._valid_analysis()) == []

    def test_missing_key_is_reported(self):
        data = self._valid_analysis()
        del data["root_cause"]
        errors = _validate_analysis(data)
        assert any("root_cause" in e for e in errors)

    def test_invalid_severity_is_reported(self):
        data = self._valid_analysis()
        data["severity"] = "extreme"
        errors = _validate_analysis(data)
        assert any("severity" in e for e in errors)

    def test_invalid_category_is_reported(self):
        data = self._valid_analysis()
        data["category"] = "unknown"
        errors = _validate_analysis(data)
        assert any("category" in e for e in errors)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Integration tests for bug_analysis_node() with mocked LLM
# ═════════════════════════════════════════════════════════════════════════════

# Sample shared state that simulates Agent 1's output
SAMPLE_STATE = {
    "raw_bug_report": (
        "Login crash on empty password\n"
        "When a user submits the login form with an empty password field, "
        "the server crashes with a NullPointerException in the auth module. "
        "This results in data loss of the current session."
    ),
    "repo_path": "/tmp/sample_repo",
    "code_map": {
        "src/auth.py":   ["login", "logout", "hash_password", "TokenManager"],
        "src/models.py": ["User", "Session"],
        "src/utils.py":  ["validate_input", "sanitize"],
    },
    "relevant_files": ["src/auth.py", "src/models.py"],
    "logs": [],
}


def _make_llm_mock(response_dict: dict):
    """Return a mock that replaces ChatOllama().invoke()."""
    mock_llm_instance = MagicMock()
    mock_response     = MagicMock()
    mock_response.content = json.dumps(response_dict)
    mock_llm_instance.invoke.return_value = mock_response
    return mock_llm_instance


VALID_LLM_RESPONSE = {
    "root_cause":           "login() does not guard against empty password, causing NullPointerException.",
    "affected_components":  ["src/auth.py::login", "src/models.py::User"],
    "severity":             "critical",
    "category":             "crash",
    "reproduction_steps":   [
        "Navigate to /login",
        "Leave password field empty",
        "Click Submit",
    ],
    "analysis_confidence":  "high",
}


class TestBugAnalysisNode:
    """Integration tests for the LangGraph node with mocked Ollama."""

    @patch("agents.bug_analysis_agent.get_ollama_model")
    def test_node_returns_all_required_state_keys(self, MockGetOllama):
        """Agent output must contain bug_analysis, severity, category, logs."""
        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)

        state = dict(SAMPLE_STATE)
        result = bug_analysis_node(state)

        assert "bug_analysis"  in result, "bug_analysis key missing from state"
        assert "severity"      in result, "severity key missing from state"
        assert "category"      in result, "category key missing from state"
        assert "logs"          in result, "logs key missing from state"

    @patch("agents.bug_analysis_agent.get_ollama_model")
    def test_bug_analysis_contains_all_required_keys(self, MockGetOllama):
        """bug_analysis dict must contain all six required keys."""
        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)

        state = dict(SAMPLE_STATE)
        result = bug_analysis_node(state)

        for key in REQUIRED_KEYS:
            assert key in result["bug_analysis"], f"Missing key in bug_analysis: {key}"

    @patch("agents.bug_analysis_agent.get_ollama_model")
    def test_severity_matches_rule_based_severity_within_one_level(self, MockGetOllama):
        """Agent severity must stay within one level of rule-based prior."""
        severity_order = ["low", "medium", "high", "critical"]

        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)
        state  = dict(SAMPLE_STATE)
        result = bug_analysis_node(state)

        prior = classify_bug(
            title       = SAMPLE_STATE["raw_bug_report"].splitlines()[0],
            description = "\n".join(SAMPLE_STATE["raw_bug_report"].splitlines()[1:]),
        )
        llm_sev  = result["severity"]
        rule_sev = prior["rule_severity"]

        llm_idx  = severity_order.index(llm_sev)
        rule_idx = severity_order.index(rule_sev)

        assert abs(llm_idx - rule_idx) <= 1, (
            f"LLM severity ({llm_sev}) differs from rule severity ({rule_sev}) by more than one level"
        )

    @patch("agents.bug_analysis_agent.get_ollama_model")
    def test_agent_only_references_files_in_code_map(self, MockGetOllama):
        """affected_components must not reference files outside the code_map."""
        response_with_hallucination = dict(VALID_LLM_RESPONSE)
        response_with_hallucination["affected_components"] = [
            "src/auth.py::login",       # valid
            "src/ghost_file.py::foo",   # hallucinated — not in code_map
        ]
        MockGetOllama.return_value = _make_llm_mock(response_with_hallucination)

        state  = dict(SAMPLE_STATE)
        result = bug_analysis_node(state)

        code_map_files = set(SAMPLE_STATE["code_map"].keys())
        for component in result["bug_analysis"]["affected_components"]:
            # component can be "file::function" or just "file"
            file_part = component.split("::")[0]
            assert file_part in code_map_files or "::" not in component, (
                f"Hallucinated file reference: {component}"
            )

    @patch("agents.bug_analysis_agent.get_ollama_model")
    def test_severity_is_valid_enum_value(self, MockGetOllama):
        """severity written to state must be one of the four valid values."""
        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)
        state  = dict(SAMPLE_STATE)
        result = bug_analysis_node(state)
        assert result["severity"] in VALID_SEVERITIES

    @patch("agents.bug_analysis_agent.get_ollama_model")
    def test_category_is_valid_enum_value(self, MockGetOllama):
        """category written to state must be one of the six valid values."""
        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)
        state  = dict(SAMPLE_STATE)
        result = bug_analysis_node(state)
        assert result["category"] in VALID_CATEGORIES

    @patch("agents.bug_analysis_agent.get_ollama_model")
    def test_log_entry_appended_with_correct_agent_name(self, MockGetOllama):
        """A log entry for BugAnalysisAgent must be appended to state['logs']."""
        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)
        state  = dict(SAMPLE_STATE)
        result = bug_analysis_node(state)

        agent_logs = [
            e for e in result["logs"]
            if e.get("agent") == "BugAnalysisAgent"
        ]
        assert len(agent_logs) >= 1, "No log entry found for BugAnalysisAgent"
        assert agent_logs[-1]["success"] is True

    @patch("agents.bug_analysis_agent.get_ollama_model")
    def test_malformed_llm_response_falls_back_gracefully(self, MockGetOllama):
        """If LLM returns invalid JSON, agent must not raise and must use fallback."""
        mock_instance          = MagicMock()
        mock_response          = MagicMock()
        mock_response.content  = "This is not JSON at all! ¯\\_(ツ)_/¯"
        mock_instance.invoke.return_value = mock_response
        MockGetOllama.return_value = mock_instance

        state  = dict(SAMPLE_STATE)
        result = bug_analysis_node(state)       # must NOT raise

        assert "bug_analysis"          in result
        assert result["severity"]      in VALID_SEVERITIES
        assert result["category"]      in VALID_CATEGORIES

    @patch("agents.bug_analysis_agent.get_ollama_model")
    def test_missing_state_keys_handled_with_empty_defaults(self, MockGetOllama):
        """Agent must handle a minimal state (no code_map or relevant_files)."""
        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)

        minimal_state = {
            "raw_bug_report": "App crashes on login.",
            "logs": [],
        }
        result = bug_analysis_node(minimal_state)   # must NOT raise
        assert "bug_analysis" in result

    @patch("agents.bug_analysis_agent.get_ollama_model")
    def test_reproduction_steps_is_a_list(self, MockGetOllama):
        """reproduction_steps in bug_analysis must always be a list."""
        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)
        state  = dict(SAMPLE_STATE)
        result = bug_analysis_node(state)
        assert isinstance(result["bug_analysis"]["reproduction_steps"], list)

    @patch("agents.bug_analysis_agent.get_ollama_model")
    def test_root_cause_is_non_empty_string(self, MockGetOllama):
        """root_cause must be a non-empty string."""
        MockGetOllama.return_value = _make_llm_mock(VALID_LLM_RESPONSE)
        state  = dict(SAMPLE_STATE)
        result = bug_analysis_node(state)
        rc = result["bug_analysis"].get("root_cause", "")
        assert isinstance(rc, str) and len(rc.strip()) > 0
