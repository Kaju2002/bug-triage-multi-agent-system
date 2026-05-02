#!/usr/bin/env python3
"""
run_full_workflow.py
Master orchestrator for all 4 agents: Code Understanding → Bug Analysis → Fix Generation → Validation
Usage: python run_full_workflow.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents.code_understanding_agent import code_understanding_node
from agents.bug_analysis_agent import bug_analysis_node
from agents.fix_generation_agent import fix_generation_node
from agents.validation_agent import validation_node


def run_full_workflow(bug_report: str, repo_path: str = ".") -> dict:
    """
    Run all 4 agents in sequence.
    
    Args:
        bug_report: The bug description/error code to analyze
        repo_path: Path to the code repository
    
    Returns:
        Final state with all results
    """
    
    # Initialize state
    state = {
        "raw_bug_report": bug_report,
        "repo_path": repo_path,
        "code_map": {},
        "relevant_files": [],
        "bug_analysis": {},
        "severity": "",
        "category": "",
        "proposed_fix": {},
        "fix_suggestion": {},
        "validation_result": {},
        "is_valid": False,
    }
    
    print("\n" + "=" * 80)
    print("🚀 MULTI-AGENT BUG TRIAGE SYSTEM")
    print("=" * 80)
    print()
    
    # ─────────────────────────────────────────────────────────────────────────
    # AGENT 1: CODE UNDERSTANDING
    # ─────────────────────────────────────────────────────────────────────────
    print("📍 STAGE 1/4: CODE UNDERSTANDING AGENT")
    print("-" * 80)
    try:
        state = code_understanding_node(state)
        print(f"✅ Code Understanding complete: {len(state['code_map'])} files found")
        print(f"   Relevant files: {state['relevant_files'][:3]}")
    except Exception as e:
        print(f"❌ Code Understanding failed: {e}")
        return state
    
    print()
    
    # ─────────────────────────────────────────────────────────────────────────
    # AGENT 2: BUG ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────
    print("📍 STAGE 2/4: BUG ANALYSIS AGENT")
    print("-" * 80)
    try:
        state = bug_analysis_node(state)
        print(f"✅ Bug Analysis complete")
        print(f"   Severity: {state['severity'].upper()}")
        print(f"   Category: {state['category'].upper()}")
        print(f"   Root Cause: {state['bug_analysis'].get('root_cause', 'N/A')[:80]}...")
    except Exception as e:
        print(f"❌ Bug Analysis failed: {e}")
        return state
    
    print()
    
    # ─────────────────────────────────────────────────────────────────────────
    # AGENT 3: FIX GENERATION
    # ─────────────────────────────────────────────────────────────────────────
    print("📍 STAGE 3/4: FIX GENERATION AGENT")
    print("-" * 80)
    try:
        state = fix_generation_node(state)
        print(f"✅ Fix Generation complete")
        print(f"   Confidence: {state['proposed_fix'].get('confidence_score', 'N/A')}")
        print(f"   Fix: {state['proposed_fix'].get('fix_description', 'N/A')[:80]}...")
    except Exception as e:
        print(f"❌ Fix Generation failed: {e}")
        return state
    
    print()
    
    # ─────────────────────────────────────────────────────────────────────────
    # AGENT 4: VALIDATION
    # ─────────────────────────────────────────────────────────────────────────
    print("📍 STAGE 4/4: VALIDATION AGENT")
    print("-" * 80)
    try:
        state = validation_node(state)
        print(f"✅ Validation complete")
        print(f"   Valid: {state['is_valid']}")
        print(f"   Confidence: {state['validation_result'].get('validation_confidence', 'N/A')}")
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return state
    
    print()
    
    return state


def print_final_report(state: dict):
    """Pretty-print the final results."""
    
    print("\n" + "=" * 80)
    print("📊 FINAL REPORT")
    print("=" * 80)
    print()
    
    print("🐛 BUG SEVERITY & CATEGORY:")
    print(f"   Severity: {state['severity'].upper()}")
    print(f"   Category: {state['category'].upper()}")
    print()
    
    print("🔍 ROOT CAUSE ANALYSIS:")
    if state['bug_analysis']:
        root_cause = state['bug_analysis'].get('root_cause', 'N/A')
        print(f"   {root_cause}")
        print()
    
    print("🛠️  PROPOSED FIX:")
    if state['proposed_fix']:
        desc = state['proposed_fix'].get('fix_description', 'N/A')
        confidence = state['proposed_fix'].get('confidence_score', 0)
        print(f"   Description: {desc}")
        print(f"   Confidence: {confidence}")
        print()
        snippet = state['proposed_fix'].get('code_snippet', '')
        if snippet:
            print(f"   Code Snippet:")
            for line in snippet.split('\n'):
                print(f"      {line}")
        print()
    
    print("✅ VALIDATION RESULT:")
    if state['validation_result']:
        valid = state['is_valid']
        print(f"   Valid: {'YES ✓' if valid else 'NO ✗'}")
        confidence = state['validation_result'].get('validation_confidence', 'N/A')
        print(f"   Confidence: {confidence}")
        
        issues = state['validation_result'].get('issues', [])
        if issues:
            print(f"   Issues:")
            for issue in issues:
                print(f"      • {issue}")
        print()
    
    print("=" * 80)


def main():
    """Main entry point."""
    
    # Example bug report - EDIT THIS!
    BUG_REPORT = """
    Hello world message not printing
    
    When we run the program, the hello world message does not print to console.
    The program runs silently without any output or error message.
    
    Expected output: hello world
    Actual output: nothing is printed
    """
    
    # Run the workflow
    state = run_full_workflow(bug_report=BUG_REPORT, repo_path=".")
    
    # Print results
    print_final_report(state)
    
    # Save to JSON
    output_file = "workflow_results.json"
    with open(output_file, "w") as f:
        json.dump(state, f, indent=2, default=str)
    print(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    main()
