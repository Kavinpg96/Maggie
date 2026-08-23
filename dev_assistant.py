"""
dev_assistant.py - Git, Build & Code Inspection Engine
"""
import os
import subprocess
from rich.console import Console

console = Console()

def handle_dev_command(query: str) -> str:
    q = query.lower().strip()
    cwd = os.getcwd()

    # Git Status
    if "git status" in q or "check git" in q:
        try:
            res = subprocess.check_output(["git", "status", "-s"], cwd=cwd, text=True, stderr=subprocess.STDOUT)
            if not res.strip():
                return "Git working directory is clean. No uncommitted changes."
            return f"Git status summary:\n{res.strip()}"
        except Exception as e:
            return f"Unable to fetch git status: {e}"

    # Git Diff / Log
    if "git diff" in q:
        try:
            res = subprocess.check_output(["git", "diff", "--stat"], cwd=cwd, text=True)
            return f"Git diff summary:\n{res.strip()}" if res else "No unstaged changes found."
        except Exception as e:
            return f"Error reading git diff: {e}"

    if "git log" in q or "recent commits" in q:
        try:
            res = subprocess.check_output(["git", "log", "-n", "3", "--oneline"], cwd=cwd, text=True)
            return f"Recent 3 commits:\n{res.strip()}"
        except Exception as e:
            return f"Error reading git log: {e}"

    # Project Build / Test Execution
    if "run tests" in q or "execute tests" in q:
        if os.path.exists(os.path.join(cwd, "pytest.ini")) or os.path.exists(os.path.join(cwd, "tests")):
            try:
                res = subprocess.check_output(["pytest", "-q"], cwd=cwd, text=True, timeout=15)
                return f"Test suite passed:\n{res.strip()}"
            except subprocess.CalledProcessError as e:
                return f"Tests failed:\n{e.output[:300]}"
            except Exception as e:
                return f"Error running tests: {e}"
        return "No test directory or pytest configuration found in this project."

    if "build project" in q or "run build" in q:
        if os.path.exists(os.path.join(cwd, "Makefile")):
            try:
                res = subprocess.check_output(["make"], cwd=cwd, text=True, timeout=20)
                return f"Build completed successfully:\n{res.strip()[:200]}"
            except subprocess.CalledProcessError as e:
                return f"Build failed with compiler error:\n{e.output[:300]}"
        return "No Makefile found in the current project root."

    return ""
