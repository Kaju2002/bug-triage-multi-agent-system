# state/logger.py
# Observability logging for all agents in the pipeline

from datetime import UTC, datetime
from typing import Any


def log_agent_run(
    state: dict,
    agent_name: str,
    input_keys: list[str],
    output_keys: list[str],
    success: bool,
    error: str | None = None,
) -> dict:
    """
    Log an agent's execution to state['logs'].

    Args:
        state: Current pipeline state (dict)
        agent_name: Name of the agent (e.g., "BugAnalysisAgent")
        input_keys: List of state keys the agent read from
        output_keys: List of state keys the agent wrote to
        success: Whether the agent ran successfully (bool)
        error: Error message if success=False (optional)

    Returns:
        Updated state with log entry appended to state['logs']
    """
    # Initialize logs list if not present
    if "logs" not in state:
        state["logs"] = []

    # Build log entry
    log_entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "agent": agent_name,
        "input_keys": input_keys,
        "output_keys": output_keys,
        "success": success,
    }

    # Add error message if present
    if error is not None:
        log_entry["error"] = error

    # Append to logs
    state["logs"].append(log_entry)

    return state
