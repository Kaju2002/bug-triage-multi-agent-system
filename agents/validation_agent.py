# agents/validation_agent.py
# Member 4 — Validation Agent (Agent 4 of 4)
# Orchestrator: LangGraph | LLM: Ollama llama3:8b (local)
#
# Receives:  state["bug_analysis"], state["fix_suggestion"]
# Produces:  state["validation_result"], state["is_valid"]

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# ── Ensure project root is importable ───────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage

from config.models import get_ollama_model
from state.logger import log_agent_run
from tools.report_writer_tool import validate_report_structure


# ── SYSTEM PROMPT ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a senior QA engineer responsible for validating bug fixes.

You are given:
1. Bug analysis (root cause, severity, affected components)
2. Fix suggestion (description, patch)

Your job:
- Validate correctness
- Check alignment with root cause
- Ensure no unsafe or incomplete fixes

Return ONLY valid JSON with EXACT keys:

{
  "is_valid": true/false,
  "issues": ["list of issues"],
  "improvement_suggestions": ["list of suggestions"],
  "validation_confidence": "high/medium/low"
}

Rules:
- Reject vague fixes
- Reject unsafe fixes (data loss, security risks)
- Ensure fix matches root cause
- Be strict but fair

Return ONLY JSON.
"""


# ── Helper: clean markdown fences ───────────────────────────────────────────

def _clean_json_response(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


# ── Main Agent Node ─────────────────────────────────────────────────────────

def validation_node(state: dict) -> dict:
    """LangGraph node — Validation Agent."""

    print("\n[ValidationAgent] Starting validation...")

    # ── 1. Read inputs ─────────────────────────────────────────────
    bug_analysis   = state.get("bug_analysis", {})
    fix_suggestion = state.get("fix_suggestion", {})

    # ── 2. Tool-based validation (structure check) ────────────────
    structure_check = validate_report_structure(bug_analysis, fix_suggestion)

    # ── 3. Prompt ────────────────────────────────────────────────
    user_prompt = f"""Bug Analysis:
{json.dumps(bug_analysis, indent=2)}

Fix Suggestion:
{json.dumps(fix_suggestion, indent=2)}

Structure Check:
{structure_check}

Validate the fix thoroughly and return ONLY JSON.
"""

    # ── 4. Call LLM ──────────────────────────────────────────────
    llm = get_ollama_model(temperature=0.1)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    print("[ValidationAgent] Calling Ollama llama3:8b...")
    response = llm.invoke(messages)
    raw_text = response.content

    # ── 5. Parse JSON ────────────────────────────────────────────
    cleaned = _clean_json_response(raw_text)

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"[ValidationAgent] JSON parse error: {e}")
        result = {
            "is_valid": False,
            "issues": ["Invalid LLM response"],
            "improvement_suggestions": ["Retry validation"],
            "validation_confidence": "low",
        }

    # ── 6. Enforce structure check ───────────────────────────────
    print(f'[DEBUG] structure_check: {structure_check}')
    if not structure_check['valid']:
        result["is_valid"] = False
        result.setdefault("issues", []).extend(structure_check["errors"])

    print(f"[ValidationAgent] Done — valid={result['is_valid']}")

    # ── 7. Write outputs ─────────────────────────────────────────
    state["validation_result"] = result
    state["is_valid"] = result["is_valid"]

    # ── 8. Logging ───────────────────────────────────────────────
    state = log_agent_run(
        state=state,
        agent_name="ValidationAgent",
        input_keys=["bug_analysis", "fix_suggestion"],
        output_keys=["validation_result", "is_valid"],
        success=True,
    )

    return state


