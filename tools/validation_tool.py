from typing import Dict, Any


def validate_fix_logic(bug_analysis: Dict[str, Any], fix: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate whether the fix addresses the root cause.

    Args:
        bug_analysis: Root cause information
        fix: Proposed fix dictionary

    Returns:
        Dict with validation result and issues
    """

    issues = []

    root = bug_analysis.get("root_cause", "").lower()
    fix_desc = fix.get("description", "").lower()

    if not root:
        issues.append("Missing root cause")

    if root and root not in fix_desc:
        issues.append("Fix does not clearly address root cause")

    return {
        "valid": len(issues) == 0,
        "issues": issues
    }