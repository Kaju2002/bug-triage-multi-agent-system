# tools/fix_suggester_tool.py
# Member 3 — Fix Generation Agent
# Rule-based fix template lookup. Provides a structured baseline fix strategy
# to the LLM to reduce hallucinations and improve output quality.

from typing import Literal

# ── Type aliases ──────────────────────────────────────────────────────────────

FixStrategy = Literal[
    "null_check",
    "boundary_check",
    "synchronization",
    "resource_management",
    "input_validation",
    "auth_hardening",
    "timeout_handling",
    "error_handling",
    "code_review",
]

# ── Pattern → strategy mapping ────────────────────────────────────────────────
# Each entry is (keywords, strategy). Evaluated in order; first match wins.
# Longer / more-specific phrases must appear before generic ones.

_PATTERN_RULES: list[tuple[list[str], FixStrategy]] = [
    (
        ["null pointer", "nullpointerexception", "none type", "nonetype",
         "attribute error", "not initialized", "uninitialized", "undefined"],
        "null_check",
    ),
    (
        ["off by one", "index out of", "out of bounds", "index error",
         "array index", "list index", "boundary", "overflow"],
        "boundary_check",
    ),
    (
        ["race condition", "concurrency", "deadlock", "thread safety",
         "mutex", "lock", "synchronize", "atomic", "concurrent"],
        "synchronization",
    ),
    (
        ["memory leak", "resource leak", "file handle", "connection not closed",
         "unclosed", "unreleased", "garbage collect", "allocation"],
        "resource_management",
    ),
    (
        ["injection", "sql injection", "command injection", "xss",
         "cross-site", "csrf", "sanitize", "unsanitized", "user input",
         "malicious input", "unescaped"],
        "input_validation",
    ),
    (
        ["authentication", "authorisation", "authorization", "session",
         "token", "credential", "privilege", "bypass", "unauthenticated",
         "unauthorized", "unauthorised"],
        "auth_hardening",
    ),
    (
        ["timeout", "latency", "slow", "performance", "response time",
         "bottleneck", "high load", "cpu", "memory usage"],
        "timeout_handling",
    ),
    (
        ["exception", "unhandled", "uncaught", "stacktrace", "traceback",
         "error propagation", "swallowed", "silent fail"],
        "error_handling",
    ),
]

# ── Fix template library ──────────────────────────────────────────────────────

_FIX_TEMPLATES: dict[FixStrategy, dict] = {
    "null_check": {
        "fix_strategy": "null_check",
        "code_pattern": (
            "# Guard against None before use\n"
            "if value is None:\n"
            "    raise ValueError(f'Expected non-None value for {param_name!r}')\n"
            "# Alternative: provide a safe default\n"
            "value = value if value is not None else default_value"
        ),
        "references": [
            "https://docs.python.org/3/library/exceptions.html#ValueError",
            "https://refactoring.guru/introduce-null-object",
        ],
    },
    "boundary_check": {
        "fix_strategy": "boundary_check",
        "code_pattern": (
            "# Validate index before accessing the collection\n"
            "if not (0 <= index < len(collection)):\n"
            "    raise IndexError(\n"
            "        f'Index {index} is out of range [0, {len(collection)})')\n"
            "return collection[index]"
        ),
        "references": [
            "https://docs.python.org/3/library/exceptions.html#IndexError",
            "https://en.wikipedia.org/wiki/Off-by-one_error",
        ],
    },
    "synchronization": {
        "fix_strategy": "synchronization",
        "code_pattern": (
            "import threading\n\n"
            "_lock = threading.Lock()\n\n"
            "def thread_safe_operation():\n"
            "    with _lock:\n"
            "        # critical section — only one thread at a time\n"
            "        shared_resource.update()"
        ),
        "references": [
            "https://docs.python.org/3/library/threading.html#lock-objects",
            "https://docs.python.org/3/library/asyncio-sync.html",
        ],
    },
    "resource_management": {
        "fix_strategy": "resource_management",
        "code_pattern": (
            "# Use context manager to guarantee resource release\n"
            "with open(file_path, 'r') as fh:\n"
            "    data = fh.read()\n"
            "# For database connections:\n"
            "with db.get_connection() as conn:\n"
            "    result = conn.execute(query)"
        ),
        "references": [
            "https://docs.python.org/3/reference/compound_stmts.html#the-with-statement",
            "https://peps.python.org/pep-0343/",
        ],
    },
    "input_validation": {
        "fix_strategy": "input_validation",
        "code_pattern": (
            "import re\n\n"
            "def validate_input(user_input: str) -> str:\n"
            "    # Allow only safe characters; reject everything else\n"
            "    if not re.fullmatch(r'[\\w\\s@.+-]+', user_input):\n"
            "        raise ValueError('Input contains disallowed characters')\n"
            "    return user_input.strip()\n\n"
            "# For SQL: always use parameterized queries\n"
            "cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))"
        ),
        "references": [
            "https://owasp.org/www-project-top-ten/",
            "https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html",
        ],
    },
    "auth_hardening": {
        "fix_strategy": "auth_hardening",
        "code_pattern": (
            "from functools import wraps\n\n"
            "def require_auth(func):\n"
            "    @wraps(func)\n"
            "    def wrapper(*args, **kwargs):\n"
            "        token = request.headers.get('Authorization')\n"
            "        if not token or not verify_token(token):\n"
            "            raise PermissionError('Authentication required')\n"
            "        return func(*args, **kwargs)\n"
            "    return wrapper"
        ),
        "references": [
            "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html",
            "https://owasp.org/www-project-top-ten/",
        ],
    },
    "timeout_handling": {
        "fix_strategy": "timeout_handling",
        "code_pattern": (
            "import signal\n\n"
            "class TimeoutError(Exception):\n"
            "    pass\n\n"
            "def _timeout_handler(signum, frame):\n"
            "    raise TimeoutError('Operation timed out')\n\n"
            "signal.signal(signal.SIGALRM, _timeout_handler)\n"
            "signal.alarm(timeout_seconds)\n"
            "try:\n"
            "    result = slow_operation()\n"
            "finally:\n"
            "    signal.alarm(0)  # cancel the alarm"
        ),
        "references": [
            "https://docs.python.org/3/library/signal.html",
            "https://docs.python.org/3/library/concurrent.futures.html",
        ],
    },
    "error_handling": {
        "fix_strategy": "error_handling",
        "code_pattern": (
            "import logging\n\n"
            "logger = logging.getLogger(__name__)\n\n"
            "try:\n"
            "    result = risky_operation()\n"
            "except SpecificError as exc:\n"
            "    logger.exception('Operation failed: %s', exc)\n"
            "    raise  # re-raise; never swallow exceptions silently\n"
            "except Exception as exc:\n"
            "    logger.critical('Unexpected error: %s', exc)\n"
            "    raise RuntimeError('Internal error — see logs') from exc"
        ),
        "references": [
            "https://docs.python.org/3/tutorial/errors.html",
            "https://docs.python.org/3/library/logging.html",
        ],
    },
    "code_review": {
        "fix_strategy": "code_review",
        "code_pattern": (
            "# Manual code review recommended.\n"
            "# Steps:\n"
            "# 1. Identify the exact line(s) where the bug manifests.\n"
            "# 2. Add defensive assertions at the function boundary.\n"
            "# 3. Write a regression test that reproduces the bug.\n"
            "# 4. Apply the minimal change that makes the test pass.\n"
            "assert invariant_condition, 'Invariant violated: describe what should be true'"
        ),
        "references": [
            "https://google.github.io/eng-practices/review/",
            "https://refactoring.guru/refactoring",
        ],
    },
}


def suggest_fix(
    root_cause: str,
    language: str,
    severity: str,
) -> dict:
    """Map a root cause description to a structured fix template.

    Performs keyword matching against known bug patterns and returns a
    fix template dict. The result is passed to the LLM as a structured
    prior to anchor its output and reduce hallucinations.

    Args:
        root_cause: A plain-English description of why the bug occurs,
            typically produced by the Bug Analysis Agent.
        language:   The programming language of the affected codebase
            (e.g. 'python', 'java', 'javascript'). Currently used as
            metadata; future versions may return language-specific snippets.
        severity:   The bug severity level ('critical', 'high', 'medium',
            'low'). Currently used as metadata for logging.

    Returns:
        A dict with keys:
            fix_strategy  (str)       — machine-readable strategy label
            code_pattern  (str)       — pseudocode / template for the fix
            references    (list[str]) — relevant documentation URLs

    Raises:
        TypeError:  If root_cause or language is not a string.
        ValueError: If root_cause is an empty string.

    Example:
        >>> result = suggest_fix(
        ...     root_cause="login() does not guard against null password",
        ...     language="python",
        ...     severity="critical",
        ... )
        >>> result["fix_strategy"]
        'null_check'
    """
    if not isinstance(root_cause, str):
        raise TypeError(f"root_cause must be str, got {type(root_cause).__name__}")
    if not isinstance(language, str):
        raise TypeError(f"language must be str, got {type(language).__name__}")
    if not root_cause.strip():
        raise ValueError("root_cause must not be empty")

    combined = root_cause.lower()

    # ── Pattern matching: first match in priority order wins ──────────────
    matched_strategy: FixStrategy = "code_review"
    for keywords, strategy in _PATTERN_RULES:
        if any(kw in combined for kw in keywords):
            matched_strategy = strategy
            break

    template = _FIX_TEMPLATES[matched_strategy].copy()

    return {
        "fix_strategy": template["fix_strategy"],
        "code_pattern": template["code_pattern"],
        "references":   template["references"],
        "language":     language,
        "severity":     severity,
    }
