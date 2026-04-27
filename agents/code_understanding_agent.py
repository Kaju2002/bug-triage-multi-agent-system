from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from state.logger import log_agent_run
from tools.code_scanner_tool import scan_codebase


def code_understanding_node(state: dict) -> dict:
    """LangGraph node — Code Understanding Agent."""

    print("\n[CodeUnderstandingAgent] Starting code analysis...")

    repo_path: str = state.get("repo_path", "")
    raw_bug_report: str = state.get("raw_bug_report", "")

    if not repo_path:
        raise ValueError("repo_path missing from state")

    # ── 1. Extract code structure using tool ─────────────────────
    code_map = scan_codebase(repo_path)

    # ── 2. Identify relevant files (simple keyword match) ────────
    relevant_files = []

    bug_text = raw_bug_report.lower()

    for file in code_map.keys():
        if any(word in file.lower() for word in bug_text.split()):
            relevant_files.append(file)

    # fallback if nothing matched
    if not relevant_files:
        relevant_files = list(code_map.keys())[:3]

    # ── 3. Update state ──────────────────────────────────────────
    state["code_map"] = code_map
    state["relevant_files"] = relevant_files

    print(f"[CodeUnderstandingAgent] Done — files={len(code_map)}")

    # ── 4. Logging ───────────────────────────────────────────────
    state = log_agent_run(
        state=state,
        agent_name="CodeUnderstandingAgent",
        input_keys=["repo_path", "raw_bug_report"],
        output_keys=["code_map", "relevant_files"],
        success=True,
    )

    return state