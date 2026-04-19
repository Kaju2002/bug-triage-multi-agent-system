# agents/bug_analysis_agent.py
# Member 2 — Bug Analysis Agent (Agent 2 of 4)
# Orchestrator: LangGraph  |  LLM: Ollama llama3:8b (fully local)
#
# Receives:  state["code_map"], state["relevant_files"], state["raw_bug_report"]
# Produces:  state["bug_analysis"], state["severity"], state["category"]

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
from tools.bug_classifier_tool import classify_bug


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a senior software engineer specialising in debugging and root-cause analysis.

Given a bug report and a map of relevant code files and functions, your task is to
perform a deep analysis of the bug.

You must return a JSON object with EXACTLY these keys:

  - root_cause:            one clear sentence describing WHY the bug occurs
  - affected_components:   list of file paths and function names involved
  - severity:              one of [critical, high, medium, low]
                             * critical — data loss, crash, security vulnerability
                             * high     — major feature broken, no workaround
                             * medium   — partial breakage, workaround exists
                             * low      — cosmetic or minor inconvenience
  - category:              one of [crash, logic_error, performance, security, ui, integration]
  - reproduction_steps:    list of strings — steps that trigger the bug (inferred if not given)
  - analysis_confidence:   high / medium / low

Rules:
  - Base your analysis STRICTLY on the provided bug report and code map
  - Do NOT reference files that are not in the code map
  - If information is insufficient, reflect this in analysis_confidence
  - Return ONLY valid JSON — no markdown fences, no preamble, no extra text
"""


# ── Helper: strip markdown fences the model sometimes adds ───────────────────

def _clean_json_response(raw: str) -> str:
    """Remove ```json ... ``` fences and leading/trailing whitespace."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


# ── Helper: validate that the LLM response has all required keys ─────────────

REQUIRED_KEYS = {
    "root_cause",
    "affected_components",
    "severity",
    "category",
    "reproduction_steps",
    "analysis_confidence",
}

VALID_SEVERITIES  = {"critical", "high", "medium", "low"}
VALID_CATEGORIES  = {"crash", "logic_error", "performance", "security", "ui", "integration"}
VALID_CONFIDENCES = {"high", "medium", "low"}


def _validate_analysis(data: dict) -> list[str]:
    """Return a list of validation error messages (empty = valid)."""
    errors: list[str] = []

    missing = REQUIRED_KEYS - data.keys()
    if missing:
        errors.append(f"Missing keys: {missing}")

    if data.get("severity") not in VALID_SEVERITIES:
        errors.append(f"Invalid severity: {data.get('severity')!r}")

    if data.get("category") not in VALID_CATEGORIES:
        errors.append(f"Invalid category: {data.get('category')!r}")

    if data.get("analysis_confidence") not in VALID_CONFIDENCES:
        errors.append(f"Invalid analysis_confidence: {data.get('analysis_confidence')!r}")

    if not isinstance(data.get("affected_components"), list):
        errors.append("affected_components must be a list")

    if not isinstance(data.get("reproduction_steps"), list):
        errors.append("reproduction_steps must be a list")

    return errors


# ── Main agent node ───────────────────────────────────────────────────────────

def bug_analysis_node(state: dict) -> dict:
    """LangGraph node — Bug Analysis Agent.

    Reads from state:
        raw_bug_report, code_map, relevant_files

    Writes to state:
        bug_analysis, severity, category, logs

    Args:
        state: The shared BugTriageState dict passed by LangGraph.

    Returns:
        Updated state with bug_analysis, severity, and category populated.
    """
    print("\n[BugAnalysisAgent] Starting analysis...")

    # ── 1. Read inputs from state ─────────────────────────────────────────
    raw_bug_report: str       = state.get("raw_bug_report", "")
    code_map:       dict      = state.get("code_map", {})
    relevant_files: list[str] = state.get("relevant_files", [])

    # ── 2. Rule-based pre-classification (reduces LLM hallucinations) ─────
    # Split raw_bug_report into title (first line) and body (rest)
    lines        = raw_bug_report.strip().splitlines()
    title        = lines[0] if lines else ""
    description  = "\n".join(lines[1:]) if len(lines) > 1 else raw_bug_report

    prior = classify_bug(title=title, description=description)
    print(f"[BugAnalysisAgent] Rule-based prior → "
          f"severity={prior['rule_severity']}, category={prior['rule_category']}, "
          f"matched={prior['matched_terms']}")

    # ── 3. Build the focused code map (only relevant files) ───────────────
    focused_map: dict = {}
    if relevant_files:
        focused_map = {f: code_map.get(f, []) for f in relevant_files if f in code_map}
    if not focused_map:
        focused_map = code_map          # fallback: send full map

    # ── 4. Compose the user prompt ────────────────────────────────────────
    user_prompt = f"""Bug Report:
\"\"\"
{raw_bug_report}
\"\"\"

Relevant Code Map (file → symbols):
{json.dumps(focused_map, indent=2)}

Rule-based pre-classification hint (use as a prior, override if your analysis differs):
  Suggested severity : {prior['rule_severity']}
  Suggested category : {prior['rule_category']}
  Matched keywords   : {prior['matched_terms']}

Now perform your deep root-cause analysis and return ONLY valid JSON.
"""

    # ── 5. Call Ollama via LangChain ──────────────────────────────────────
    llm = get_ollama_model(temperature=0.1)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    print("[BugAnalysisAgent] Calling Ollama llama3:8b...")
    response = llm.invoke(messages)
    raw_text = response.content

    # ── 6. Parse and validate the response ───────────────────────────────
    cleaned = _clean_json_response(raw_text)

    try:
        analysis: dict = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        print(f"[BugAnalysisAgent] JSON parse error: {exc}")
        print(f"[BugAnalysisAgent] Raw response:\n{raw_text}")
        # Fallback: return a low-confidence placeholder so the pipeline continues
        analysis = {
            "root_cause":           "Unable to parse LLM response — see logs.",
            "affected_components":  [],
            "severity":             prior["rule_severity"],
            "category":             prior["rule_category"],
            "reproduction_steps":   [],
            "analysis_confidence":  "low",
        }

    # ── 7. Validate required keys & enum values ───────────────────────────
    errors = _validate_analysis(analysis)
    if errors:
        print(f"[BugAnalysisAgent] Validation warnings: {errors}")
        # Auto-repair from rule-based prior where possible
        if "severity" not in analysis or analysis["severity"] not in VALID_SEVERITIES:
            analysis["severity"] = prior["rule_severity"]
        if "category" not in analysis or analysis["category"] not in VALID_CATEGORIES:
            analysis["category"] = prior["rule_category"]
        if "affected_components" not in analysis:
            analysis["affected_components"] = []
        if "reproduction_steps" not in analysis:
            analysis["reproduction_steps"] = []
        if "analysis_confidence" not in analysis:
            analysis["analysis_confidence"] = "low"
        if "root_cause" not in analysis:
            analysis["root_cause"] = "Root cause could not be determined."

    # ── 8. Hallucination filter — remove components not in code_map ──────
    # The LLM can invent file names. Strip any affected_component whose file
    # part is not present in the provided code_map.
    if code_map and isinstance(analysis.get("affected_components"), list):
        filtered = []
        for component in analysis["affected_components"]:
            file_part = component.split("::")[0].strip()
            if file_part in code_map:
                filtered.append(component)
            else:
                print(f"[BugAnalysisAgent] Removing hallucinated component: {component!r}")
        analysis["affected_components"] = filtered

    print(f"[BugAnalysisAgent] Done — "
          f"severity={analysis['severity']}, "
          f"category={analysis['category']}, "
          f"confidence={analysis['analysis_confidence']}")

    # ── 9. Write outputs to state ─────────────────────────────────────────
    state["bug_analysis"] = analysis
    state["severity"]     = analysis["severity"]
    state["category"]     = analysis["category"]

    # ── 10. Log this agent run ────────────────────────────────────────────
    state = log_agent_run(
        state       = state,
        agent_name  = "BugAnalysisAgent",
        input_keys  = ["raw_bug_report", "code_map", "relevant_files"],
        output_keys = ["bug_analysis", "severity", "category"],
        success     = True,
    )

    return state
