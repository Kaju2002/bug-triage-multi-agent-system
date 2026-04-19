# test_agent_live.py
# Test Member 2's agent with REAL Ollama service
# Make sure: Terminal 1 has "ollama serve" running
#            Terminal 2 has completed "ollama pull llama3:8b"

import json
import sys
from pathlib import Path

# Make project importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents.bug_analysis_agent import bug_analysis_node

def main():
    """Test the bug analysis agent with a real bug report."""
    
    print("=" * 70)
    print("🚀 TESTING MEMBER 2: BUG ANALYSIS AGENT (WITH REAL OLLAMA)")
    print("=" * 70)
    print()
    
    # Simulate what Member 1 agent would output
    sample_state = {
        "raw_bug_report": """
Login crashes on empty password.

When a user submits the login form with an empty password field,
the server crashes with a NullPointerException in the auth module.
This results in data loss of the current session.

Error message: java.lang.NullPointerException at auth.login() line 45
""",
        "code_map": {
            "src/auth.py": ["login", "logout", "hash_password", "TokenManager"],
            "src/models.py": ["User", "Session", "Password"],
            "src/utils.py": ["validate_input", "sanitize", "hash"],
        },
        "relevant_files": ["src/auth.py", "src/models.py"],
        "logs": [],
    }
    
    print("📋 INPUT BUG REPORT:")
    print("-" * 70)
    print(sample_state["raw_bug_report"])
    print("-" * 70)
    print()
    
    print("🔄 Analyzing with Ollama LLM (llama3:8b)...")
    print("⏳ This may take 5-10 seconds on first run...")
    print()
    
    try:
        # Run the agent with REAL Ollama
        result = bug_analysis_node(sample_state)
        
        print("✅ SUCCESS! Agent completed analysis.")
        print()
        
        # Display results
        print("=" * 70)
        print("📊 AGENT ANALYSIS OUTPUT:")
        print("=" * 70)
        print()
        
        analysis = result["bug_analysis"]
        print(f"🔍 ROOT CAUSE:")
        print(f"   {analysis['root_cause']}")
        print()
        
        print(f"🚨 SEVERITY: {result['severity'].upper()}")
        print(f"📂 CATEGORY: {result['category'].upper()}")
        print(f"💡 CONFIDENCE: {analysis['analysis_confidence'].upper()}")
        print()
        
        print(f"🎯 AFFECTED COMPONENTS:")
        for comp in analysis['affected_components']:
            print(f"   • {comp}")
        print()
        
        print(f"📝 REPRODUCTION STEPS:")
        for i, step in enumerate(analysis['reproduction_steps'], 1):
            print(f"   {i}. {step}")
        print()
        
        # Show full JSON
        print("=" * 70)
        print("📄 FULL JSON OUTPUT:")
        print("=" * 70)
        print(json.dumps(analysis, indent=2))
        print()
        
        print("=" * 70)
        print("✅ MEMBER 2 COMPONENT WORKING CORRECTLY WITH REAL OLLAMA!")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()
        print("Troubleshooting:")
        print("1. Make sure Terminal 1 has 'ollama serve' running")
        print("2. Make sure Terminal 2 completed 'ollama pull llama3:8b'")
        print("3. Check .env file has OLLAMA_BASE_URL=http://localhost:11434")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
