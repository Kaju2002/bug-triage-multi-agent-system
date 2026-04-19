# config/settings.py
# Global configuration for the Bug Triage Multi-Agent System
# Load environment variables from .env file

import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# ── Ollama Configuration ──────────────────────────────────────────────────────

# Base URL for Ollama service. Default: localhost:11434
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Default Ollama model name. Default: llama3:8b
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")

# ── LLM Generation Parameters ─────────────────────────────────────────────────

# Temperature for LLM responses (0.0 = deterministic, 1.0 = creative)
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.1"))

# Maximum tokens for LLM output
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "2048"))

# ── Logging & Output ──────────────────────────────────────────────────────────

# Directory where reports and logs are saved
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

# Log format: 'jsonl' or 'json'
LOG_FORMAT = os.getenv("LOG_FORMAT", "jsonl")

# ── Development / Debug ───────────────────────────────────────────────────────

# Enable debug mode with verbose logging
DEBUG = os.getenv("DEBUG", "False").lower() == "true"