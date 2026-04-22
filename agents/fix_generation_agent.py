# agents/fix_generation_agent.py
# Member 3 — Fix Generation Agent (Agent 3 of 4)
# Orchestrator: LangGraph  |  LLM: Ollama llama3:8b (fully local)
#
# Receives:  state["bug_analysis"], state["raw_bug_report"], state["code_map"]
# Produces:  state["proposed_fix"], state["fix_suggestion"]

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# ── Make sure the project root is on sys.path when running directly ──────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage

from config.models import get_ollama_model
from state.logger import log_agent_run
from tools.fix_suggester_tool import suggest_fix


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a senior software engineer specializing in bug remediation. You produce precise, safe, and minimal code fixes.

Given a bug analysis (root cause, severity, affected components) and relevant code context,
generate a concrete, implementable fix.

You must return a JSON object with EXACTLY these keys:

  - fix_description:  one or two sentences describing the fix in plain English
                      (minimum 20 characters, must directly address the root cause)
  - code_snippet:     pseudocode or actual code that implements the fix
                      (minimum 20 characters, must be concrete — no vague placeholders)
  - confidence_score: a float between 0.0 and 1.0 indicating your confidence in this fix
                        * 0.9–1.0 — highly confident, root cause is clear and fix is targeted
                        * 0.6–0.9 — reasonably confident, fix addresses likely root cause
                        * 0.3–0.6 — moderate confidence, some uncertainty remains
                        * 0.0–0.3 — low confidence, insufficient information

Rules:
  - The fix MUST directly address the stated root cause
  - Do NOT introduce new security vulnerabilities
  - Do NOT suggest full rewrites; produce minimal, targeted changes
  - Never generate placeholder text like "# TODO" or "pass" as the entire snippet
  - Return ONLY valid JSON — no markdown fences, no preamble, no extra text
"""


# ── Helper: strip markdown fences the model sometimes adds ───────────────────

def _clean_json_response(raw: str) -> str:
    """Remove ```json ... ``` fences and leading/trailing whitespace.

    Args:
        raw: Raw string from the LLM response.

    Returns:
        Cleaned string with fences and surrounding whitespace removed.
    """
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


# ── Quality-filter constants ──────────────────────────────────────────────────

_MIN_DESCRIPTION_LEN: int = 20
_MIN_SNIPPET_LEN: int = 20

_REFUSAL_PHRASES: list[str] = [
    "i cannot",
    "i'm unable",
    "i am unable",
    "as an ai",
    "i don't know",
    "i do not know",
    "cannot provide",
    "unable to provide",
    "not able to",
    "no information",
    "i apologize",
]


def _passes_quality_filter(result: dict) -> bool:
    """Return True if the parsed LLM response meets minimum quality thresholds.

    Checks three criteria:
      1. fix_description and code_snippet each meet a minimum character length.
      2. Neither field contains known LLM refusal phrases.
      3. confidence_score is a parseable float in [0.0, 1.0].

    Args:
        result: Parsed dict from the LLM JSON response.

    Returns:
        True if all quality checks pass; False otherwise.
    """
    fix_desc  = str(result.get("fix_description", "")).strip()
    code_snip = str(result.get("code_snippet",    "")).strip()
    raw_conf  = result.get("confidence_score", None)

    # ── Length checks ─────────────────────────────────────────────────────
    if len(fix_desc) < _MIN_DESCRIPTION_LEN:
        print(
            f"[FixGenerationAgent] Quality filter: fix_description too short "
            f"({len(fix_desc)} chars, min={_MIN_DESCRIPTION_LEN})"
        )
        return False

    if len(code_snip) < _MIN_SNIPPET_LEN:
        print(
            f"[FixGenerationAgent] Quality filter: code_snippet too short "
            f"({len(code_snip)} chars, min={_MIN_SNIPPET_LEN})"
        )
        return False

    # ── Refusal-phrase check ──────────────────────────────────────────────
    combined_lower = (fix_desc + " " + code_snip).lower()
    for phrase in _REFUSAL_PHRASES:
        if phrase in combined_lower:
            print(f"[FixGenerationAgent] Quality filter: refusal phrase detected: {phrase!r}")
            return False

    # ── Confidence-score range check ──────────────────────────────────────
    try:
        score = float(raw_conf)
    except (TypeError, ValueError):
        print(f"[FixGenerationAgent] Quality filter: invalid confidence_score: {raw_conf!r}")
        return False

    if not (0.0 <= score <= 1.0):
        print(f"[FixGenerationAgent] Quality filter: confidence_score out of range: {score}")
        return False

    return True


def _score_to_level(score: float) -> str:
    """Convert a 0.0–1.0 confidence float to a high/medium/low label.

    Used to populate the fix_suggestion["confidence"] field that the
    Validation Agent's validate_report_structure tool expects.

    Args:
        score: Confidence float in [0.0, 1.0].

    Returns:
        'high' for score >= 0.7, 'medium' for >= 0.4, 'low' otherwise.
    """
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


# ── Main agent node ───────────────────────────────────────────────────────────

def fix_generation_node(state: dict) -> dict:
    """LangGraph node — Fix Generation Agent.

    Reads from state:
        bug_analysis, raw_bug_report, code_map

    Writes to state:
        proposed_fix   — full fix schema consumed by downstream agents
        fix_suggestion — Agent-4-compatible alias (fix_description, code_patch, confidence)
        logs           — appended log entry

    Args:
        state: The shared BugTriageState dict passed by LangGraph.

    Returns:
        Updated state with proposed_fix and fix_suggestion populated.
    """
    print("\n[FixGenerationAgent] Starting fix generation...")

    # ── 1. Read inputs from state ─────────────────────────────────────────
    bug_analysis:   dict      = state.get("bug_analysis",   {})
    raw_bug_report: str       = state.get("raw_bug_report", "")
    code_map:       dict      = state.get("code_map",       {})

    root_cause: str = bug_analysis.get("root_cause", "")
    severity:   str = bug_analysis.get("severity",   "medium")

    # ── 2. Rule-based fix suggestion (grounded baseline) ──────────────────
    tool_result = suggest_fix(
        root_cause=root_cause or "unknown root cause",
        language="python",
        severity=severity,
    )
    print(f"[FixGenerationAgent] Rule-based strategy → {tool_result['fix_strategy']}")

    # ── 3. Compose the user prompt ────────────────────────────────────────
    user_prompt = f"""Bug Analysis:
{json.dumps(bug_analysis, indent=2)}

Bug Report (raw):
\"\"\"
{raw_bug_report}
\"\"\"

Relevant Code Context (file → symbols):
{json.dumps(code_map, indent=2)}

Rule-based fix strategy hint: {tool_result['fix_strategy']}
Code pattern template:
{tool_result['code_pattern']}

Generate a concrete, minimal fix for this bug and return ONLY valid JSON.
"""

    # ── 4. Call Ollama via LangChain ──────────────────────────────────────
    llm = get_ollama_model(temperature=0.2)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    print("[FixGenerationAgent] Calling Ollama llama3:8b...")
    response = llm.invoke(messages)
    raw_text = response.content

    # ── 5. Parse the LLM response ─────────────────────────────────────────
    cleaned = _clean_json_response(raw_text)

    llm_result: dict = {}
    try:
        llm_result = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        print(f"[FixGenerationAgent] JSON parse error: {exc}")
        print(f"[FixGenerationAgent] Raw response:\n{raw_text}")

    # ── 6. Quality / hallucination filter ────────────────────────────────
    # If the LLM produced usable output, use it; otherwise fall back to the
    # rule-based tool so the pipeline always continues with valid data.
    llm_used: bool = bool(llm_result) and _passes_quality_filter(llm_result)

    if llm_used:
        fix_description:  str   = str(llm_result["fix_description"])
        code_snippet:     str   = str(llm_result["code_snippet"])
        confidence_score: float = float(llm_result["confidence_score"])
        print(f"[FixGenerationAgent] LLM output accepted (confidence={confidence_score:.2f})")
    else:
        print("[FixGenerationAgent] Falling back to rule-based fix template.")
        fix_description  = (
            f"Apply {tool_result['fix_strategy'].replace('_', ' ')} pattern "
            f"to address: {root_cause or 'the identified root cause'}"
        )
        code_snippet     = tool_result["code_pattern"]
        confidence_score = 0.4   # conservative fallback confidence

    # ── 7. Build proposed_fix (full schema) ───────────────────────────────
    proposed_fix: dict = {
        "fix_description":  fix_description,
        "code_snippet":     code_snippet,
        "fix_strategy":     tool_result["fix_strategy"],
        "confidence_score": confidence_score,
        "references":       tool_result["references"],
        "llm_used":         llm_used,
    }

    # ── 8. Build fix_suggestion (Agent 4 / validate_report_structure compat) ─
    # validate_report_structure checks for fix_description, code_patch, confidence.
    fix_suggestion: dict = {
        "fix_description": fix_description,
        "code_patch":      code_snippet,
        "confidence":      _score_to_level(confidence_score),
    }

    print(
        f"[FixGenerationAgent] Done — "
        f"strategy={tool_result['fix_strategy']}, "
        f"confidence={confidence_score:.2f}, "
        f"llm_used={llm_used}"
    )

    # ── 9. Write outputs to state ─────────────────────────────────────────
    state["proposed_fix"]   = proposed_fix
    state["fix_suggestion"] = fix_suggestion

    # ── 10. Log this agent run ────────────────────────────────────────────
    state = log_agent_run(
        state       = state,
        agent_name  = "FixGenerationAgent",
        input_keys  = ["bug_analysis", "raw_bug_report", "code_map"],
        output_keys = ["proposed_fix", "fix_suggestion"],
        success     = True,
    )

    return state
