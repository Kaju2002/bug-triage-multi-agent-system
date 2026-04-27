from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
import tempfile

from tools.code_scanner_tool import scan_codebase
from agents.code_understanding_agent import code_understanding_node


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Tool Tests (scan_codebase)
# ═════════════════════════════════════════════════════════════════════════════

def test_scan_codebase_extracts_functions_and_classes():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "sample.py")

        with open(file_path, "w") as f:
            f.write("""
def foo():
    pass

class Bar:
    pass
""")

        result = scan_codebase(tmpdir)

        assert "sample.py" in result
        assert "foo" in result["sample.py"]
        assert "Bar" in result["sample.py"]


def test_scan_codebase_empty_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = scan_codebase(tmpdir)
        assert result == {}


def test_scan_codebase_invalid_path():
    try:
        scan_codebase("invalid/path")
    except ValueError as e:
        assert "does not exist" in str(e)


def test_scan_codebase_ignores_non_py_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "text.txt")

        with open(file_path, "w") as f:
            f.write("just text")

        result = scan_codebase(tmpdir)
        assert result == {}


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Agent Tests (code_understanding_node)
# ═════════════════════════════════════════════════════════════════════════════

def test_agent_returns_code_map_and_relevant_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "auth.py")

        with open(file_path, "w") as f:
            f.write("def login(): pass")

        state = {
            "repo_path": tmpdir,
            "raw_bug_report": "login error",
            "logs": []
        }

        result = code_understanding_node(state)

        assert "code_map" in result
        assert "relevant_files" in result


def test_agent_detects_relevant_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "auth.py")

        with open(file_path, "w") as f:
            f.write("def login(): pass")

        state = {
            "repo_path": tmpdir,
            "raw_bug_report": "login fails",
            "logs": []
        }

        result = code_understanding_node(state)

        assert "auth.py" in result["relevant_files"]


def test_agent_fallback_relevant_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "utils.py")

        with open(file_path, "w") as f:
            f.write("def helper(): pass")

        state = {
            "repo_path": tmpdir,
            "raw_bug_report": "unrelated issue",
            "logs": []
        }

        result = code_understanding_node(state)

        assert len(result["relevant_files"]) > 0


def test_agent_logs_added():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "a.py")

        with open(file_path, "w") as f:
            f.write("def x(): pass")

        state = {
            "repo_path": tmpdir,
            "raw_bug_report": "",
            "logs": []
        }

        result = code_understanding_node(state)

        assert len(result["logs"]) > 0
        assert result["logs"][-1]["agent"] == "CodeUnderstandingAgent"


def test_agent_missing_repo_path():
    state = {"logs": []}

    try:
        code_understanding_node(state)
    except ValueError as e:
        assert "repo_path" in str(e)