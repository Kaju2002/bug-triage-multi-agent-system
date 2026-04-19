# tools/bug_classifier_tool.py
# Member 2 — Bug Analysis Agent
# Keyword-based pre-classifier. Provides a rule-based prior to the LLM
# to reduce hallucinations and improve structured output quality.

from typing import Literal

# ── Type aliases ─────────────────────────────────────────────────────────────

SeverityLevel = Literal["critical", "high", "medium", "low"]
CategoryLabel = Literal[
    "crash", "logic_error", "performance", "security", "ui", "integration"
]

# ── Keyword dictionaries ──────────────────────────────────────────────────────
# Ordered from highest to lowest priority. First match wins for severity.

SEVERITY_KEYWORDS: dict[str, list[str]] = {
    "critical": [
        "data loss", "corruption", "null pointer", "segfault",
        "security", "authentication", "unauthorised", "unauthorized",
        "crash", "breach", "exploit", "remote code execution", "rce",
    ],
    "high": [
        "broken", "fails", "cannot", "unable", "500 error",
        "exception", "traceback", "throws", "error", "failure",
        "not working", "blocked",
    ],
    # NOTE: 'low' is checked BEFORE 'medium' so cosmetic/UI bugs
    # (e.g. "button colour wrong") are not promoted by generic words
    # like "does not match" which would otherwise trip the medium bucket.
    "low": [
        "cosmetic", "typo", "alignment", "colour", "color",
        "style", "minor", "nitpick",
    ],
    "medium": [
        "incorrect", "wrong", "unexpected", "intermittent",
        "sometimes", "occasionally", "inconsistent",
    ],
}

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "crash":       ["crash", "null pointer", "segfault", "killed", "core dump", "abort"],
    "logic_error": ["wrong result", "incorrect", "off by one", "logic", "miscalculation",
                    "wrong value", "invalid result"],
    "performance": ["slow", "timeout", "memory", "cpu", "leak", "lag", "high load",
                    "bottleneck", "latency"],
    "security":    ["auth", "injection", "xss", "csrf", "privilege", "bypass",
                    "token", "session", "password", "credential"],
    "ui":          ["display", "render", "layout", "button", "modal", "page",
                    "screen", "ui", "ux", "frontend", "visual"],
    "integration": ["api", "network", "database", "connection", "404", "timeout",
                    "endpoint", "webhook", "service", "third-party"],
}


def classify_bug(
    title: str,
    description: str,
    error_message: str | None = None,
) -> dict:
    """Apply keyword-based pre-classification to a bug report.

    Checks title, description, and optional error message against
    known severity and category keyword sets. This result is passed
    to the LLM as a prior to reduce hallucinations.

    Args:
        title:         One-line bug title.
        description:   Full bug description text.
        error_message: Optional error/exception/stacktrace string.

    Returns:
        A dict with keys:
            rule_severity  (str)  — keyword-matched severity level
            rule_category  (str)  — keyword-matched category
            matched_terms  (list) — all matched keywords
            text_length    (int)  — total character count analysed

    Raises:
        ValueError: If both title and description are empty strings.
    """
    if not title.strip() and not description.strip():
        raise ValueError("title and description cannot both be empty")

    combined = " ".join([title, description, error_message or ""]).lower()

    matched: list[str] = []

    # ── Severity: first match in priority order wins ───────────────────────
    # Order: critical > high > low > medium
    # 'low' is checked before 'medium' so cosmetic keywords (colour, typo)
    # are not overridden by generic words like "does not match" (medium bucket).
    severity: SeverityLevel = "low"
    for level in ("critical", "high", "low", "medium"):
        hits = [kw for kw in SEVERITY_KEYWORDS[level] if kw in combined]
        if hits:
            matched.extend(hits)
            severity = level  # type: ignore[assignment]
            break

    # ── Category: first match wins ─────────────────────────────────────────
    category: CategoryLabel = "logic_error"
    for cat, keywords in CATEGORY_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in combined]
        if hits:
            matched.extend(hits)
            category = cat  # type: ignore[assignment]
            break

    return {
        "rule_severity": severity,
        "rule_category": category,
        "matched_terms": list(set(matched)),
        "text_length":   len(combined),
    }