# tools/report_writer_tool.py

from typing import Dict, Any


def validate_report_structure(
    bug_analysis: Dict[str, Any],
    fix_suggestion: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate structure of bug analysis and fix suggestion.

    Returns:
        dict:
            valid: bool
            errors: list[str]
    """

    errors = []

    # ── Bug Analysis Checks ─────────────────────────────
    required_analysis_keys = [
        "root_cause",
        "affected_components",
        "severity",
        "category",
    ]

    for key in required_analysis_keys:
        if key not in bug_analysis:
            errors.append(f"Missing bug_analysis key: {key}")

    # ── Fix Suggestion Checks ───────────────────────────
    required_fix_keys = [
        "fix_description",
        "code_patch",
        "confidence",
    ]

    for key in required_fix_keys:
        if key not in fix_suggestion:
            errors.append(f"Missing fix_suggestion key: {key}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }