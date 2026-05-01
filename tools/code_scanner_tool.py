from typing import Dict, List
import os
import ast


def scan_codebase(repo_path: str) -> Dict[str, List[str]]:
    """
    Scan a repository and extract structure from Python files.

    This tool walks through the given repository path, parses all .py files,
    and extracts function and class names using Python's AST module.

    Args:
        repo_path: Path to the repository folder.

    Returns:
        A dictionary mapping file paths to a list of function and class names.

    Raises:
        ValueError: If repo_path does not exist or is not a directory.
    """

    if not os.path.exists(repo_path):
        raise ValueError("Repository path does not exist")

    if not os.path.isdir(repo_path):
        raise ValueError("Provided path is not a directory")

    code_map: Dict[str, List[str]] = {}

    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        source = f.read()

                    tree = ast.parse(source)

                    symbols: List[str] = []

                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            symbols.append(node.name)
                        elif isinstance(node, ast.ClassDef):
                            symbols.append(node.name)

                    if symbols:
                        # Use relative path (cleaner for your system)
                        rel_path = os.path.relpath(file_path, repo_path)
                        code_map[rel_path] = list(set(symbols))

                except Exception:
                    # Skip problematic files
                    continue

    return code_map