from agents.validation_agent import validation_node

state = {
    "suggested_fixes": [
        {"fix_title": "Fix null pointer", "target_function": "login"}
    ],
    "severity": "high",
    "logs": [],
}

result = validation_node(state)

print(result["test_cases"])