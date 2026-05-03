#!/usr/bin/env python3
"""
main.py
Multi-Agent Bug Triage System Orchestrator
Chains 4 agents in sequence: Code Understanding → Bug Analysis → Fix Generation → Validation
SE4010 - CTSE Assignment 2
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents.code_understanding_agent import code_understanding_node
from agents.bug_analysis_agent import bug_analysis_node
from agents.fix_generation_agent import fix_generation_node
from agents.validation_agent import validation_node


class BugTriageOrchestrator:
    """Orchestrates 4-agent multi-agent system for bug triage."""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
    
    def initialize_state(self, bug_report: str, repo_path: str = ".") -> dict:
        """Initialize the shared state dictionary."""
        return {
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
    
    def run_agent_1_code_understanding(self, state: dict) -> dict:
        """Agent 1: Understand the codebase structure."""
        print("\n" + "=" * 80)
        print("📍 AGENT 1/4: CODE UNDERSTANDING")
        print("=" * 80)
        print(" Scanning codebase structure...")
        
        try:
            state = code_understanding_node(state)
            files_count = len(state['code_map'])
            relevant_count = len(state['relevant_files'])
            
            print(f" Agent 1 Complete")
            print(f"   Found: {files_count} files")
            print(f"   Relevant: {relevant_count} files")
            print(f"   Files: {state['relevant_files'][:3]}")
            
            self.results["agent_1"] = {
                "status": "success",
                "files_found": files_count,
                "relevant_files": state['relevant_files']
            }
            return state
            
        except Exception as e:
            print(f" Agent 1 FAILED: {e}")
            self.results["agent_1"] = {"status": "failed", "error": str(e)}
            raise
    
    def run_agent_2_bug_analysis(self, state: dict) -> dict:
        """Agent 2: Analyze the bug and find root cause."""
        print("\n" + "=" * 80)
        print("📍 AGENT 2/4: BUG ANALYSIS")
        print("=" * 80)
        print(" Analyzing bug report...")
        
        try:
            state = bug_analysis_node(state)
            
            root_cause = state['bug_analysis'].get('root_cause', 'Unknown')
            severity = state.get('severity', 'Unknown').upper()
            category = state.get('category', 'Unknown').upper()
            confidence = state['bug_analysis'].get('analysis_confidence', 'low')
            
            print(f" Agent 2 Complete")
            print(f"   Severity: {severity}")
            print(f"   Category: {category}")
            print(f"   Root Cause: {root_cause[:100]}...")
            print(f"   Confidence: {confidence}")
            
            self.results["agent_2"] = {
                "status": "success",
                "severity": severity,
                "category": category,
                "root_cause": root_cause,
                "confidence": confidence
            }
            return state
            
        except Exception as e:
            print(f" Agent 2 FAILED: {e}")
            self.results["agent_2"] = {"status": "failed", "error": str(e)}
            raise
    
    def run_agent_3_fix_generation(self, state: dict) -> dict:
        """Agent 3: Generate a fix for the bug."""
        print("\n" + "=" * 80)
        print("📍 AGENT 3/4: FIX GENERATION")
        print("=" * 80)
        print("  Generating fix...")
        
        try:
            state = fix_generation_node(state)
            
            fix_desc = state['proposed_fix'].get('fix_description', 'N/A')
            confidence = state['proposed_fix'].get('confidence_score', 0)
            code_snippet = state['proposed_fix'].get('code_snippet', '')[:200]
            
            print(f"  Agent 3 Complete")
            print(f"   Description: {fix_desc[:80]}...")
            print(f"   Confidence: {confidence}")
            print(f"   Code Length: {len(code_snippet)} chars")
            
            # Display references
            references = state['proposed_fix'].get('references', [])
            if references:
                print(f"    References:")
                for ref in references:
                    print(f"      🔗 {ref}")
            
            self.results["agent_3"] = {
                "status": "success",
                "fix_description": fix_desc,
                "confidence": confidence,
                "code_snippet_preview": code_snippet
            }
            return state
            
        except Exception as e:
            print(f" Agent 3 FAILED: {e}")
            self.results["agent_3"] = {"status": "failed", "error": str(e)}
            raise
    
    def run_agent_4_validation(self, state: dict) -> dict:
        """Agent 4: Validate the proposed fix."""
        print("\n" + "=" * 80)
        print("📍 AGENT 4/4: VALIDATION")
        print("=" * 80)
        print("  Validating fix...")
        
        try:
            state = validation_node(state)
            
            is_valid = state.get('is_valid', False)
            confidence = state['validation_result'].get('validation_confidence', 'low')
            issues = state['validation_result'].get('issues', [])
            
            print(f" Agent 4 Complete")
            print(f"   Valid: {'YES ✓' if is_valid else 'NO ✗'}")
            print(f"   Confidence: {confidence}")
            if issues:
                print(f"   Issues: {len(issues)}")
                for issue in issues[:2]:
                    print(f"      • {issue}")
            
            self.results["agent_4"] = {
                "status": "success",
                "is_valid": is_valid,
                "confidence": confidence,
                "issues": issues
            }
            return state
            
        except Exception as e:
            print(f" Agent 4 FAILED: {e}")
            self.results["agent_4"] = {"status": "failed", "error": str(e)}
            raise
    
    def run_workflow(self, bug_report: str, repo_path: str = ".") -> dict:
        """Execute the full 4-agent workflow."""
        self.start_time = datetime.now()
        state = self.initialize_state(bug_report, repo_path)
        
        print("\n" + "╔" + "=" * 78 + "╗")
        print("║" + " " * 20 + "🚀 MULTI-AGENT BUG TRIAGE SYSTEM" + " " * 25 + "║")
        print("║" + " " * 22 + "SE4010 - CTSE Assignment 2" + " " * 30 + "║")
        print("╚" + "=" * 78 + "╝")
        
        try:
            state = self.run_agent_1_code_understanding(state)
            state = self.run_agent_2_bug_analysis(state)
            state = self.run_agent_3_fix_generation(state)
            state = self.run_agent_4_validation(state)
            
            return state
            
        except Exception as e:
            print(f"\n WORKFLOW FAILED: {e}")
            raise
    
    def print_final_report(self, state: dict):
        """Print comprehensive final report."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "=" * 80)
        print(" FINAL TRIAGE REPORT")
        print("=" * 80)
        print()
        
        # Bug Classification
        print(" BUG CLASSIFICATION:")
        print(f"   Severity: {state.get('severity', 'UNKNOWN').upper()}")
        print(f"   Category: {state.get('category', 'UNKNOWN').upper()}")
        print()
        
        # Root Cause
        print(" ROOT CAUSE ANALYSIS:")
        root_cause = state['bug_analysis'].get('root_cause', 'Unable to determine')
        print(f"   {root_cause}")
        components = state['bug_analysis'].get('affected_components', [])
        if components:
            print(f"   Affected Components: {', '.join(components[:3])}")
        print()
        
        # Proposed Fix
        print("  PROPOSED FIX:")
        fix_desc = state['proposed_fix'].get('fix_description', 'N/A')
        confidence = state['proposed_fix'].get('confidence_score', 0)
        print(f"   {fix_desc}")
        print(f"   Confidence: {confidence:.0%}")
        
        code = state['proposed_fix'].get('code_snippet', '')
        if code:
            print(f"\n   Code Solution:")
            for line in code.split('\n')[:10]:
                print(f"      {line}")
            if len(code.split('\n')) > 10:
                print(f"      ... ({len(code.split('\n')) - 10} more lines)")
        
        # References/Documentation
        references = state['proposed_fix'].get('references', [])
        if references:
            print(f"\n    References/Documentation:")
            for ref in references:
                print(f"      🔗 {ref}")
        print()
        
        # Validation
        print(" VALIDATION RESULT:")
        is_valid = state.get('is_valid', False)
        print(f"   Status: {'APPROVED ' if is_valid else 'REJECTED '}")
        val_conf = state['validation_result'].get('validation_confidence', 'low')
        print(f"   Confidence: {val_conf}")
        
        issues = state['validation_result'].get('issues', [])
        if issues:
            print(f"   Issues ({len(issues)}):")
            for issue in issues:
                print(f"        {issue}")
        print()
        
        # Summary
        print("  EXECUTION TIME: {:.2f}s".format(elapsed))
        print("=" * 80)
    
    def save_results(self, state: dict, filename: str = "workflow_results.json"):
        """Save full results to JSON file."""
        output = {
            "timestamp": datetime.now().isoformat(),
            "bug_report": state.get('raw_bug_report', ''),
            "agents": self.results,
            "state": state,
        }
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        print(f"\n Full results saved to: {filename}")


def main():
    """Main entry point."""
    
    orchestrator = BugTriageOrchestrator()
    
    # ┌──────────────────────────────────────────────────────────────────────────┐
    # │ EDIT YOUR BUG REPORT HERE                                               │
    # └──────────────────────────────────────────────────────────────────────────┘
    
    BUG_REPORT = """
    Print hello function not working
    
    The code has:
    print('hello')
    
    But nothing prints to console. The function should print hello to the console output.
    
    Expected: hello appears in console
    Actual: nothing is printed
    """
    
    # ┌──────────────────────────────────────────────────────────────────────────┐
    
    try:
        # Run the full workflow
        state = orchestrator.run_workflow(bug_report=BUG_REPORT, repo_path=".")
        
        # Print results
        orchestrator.print_final_report(state)
        
        # Save to file
        orchestrator.save_results(state)
        
        print("\n WORKFLOW COMPLETED SUCCESSFULLY\n")
        
    except Exception as e:
        print(f"\n WORKFLOW FAILED: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
