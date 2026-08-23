"""
file_search.py - Deep File Finder and Reader
"""
import os
import subprocess
from config import FILE_SEARCH_ROOT

_TEXT_EXTS = {".txt", ".md", ".py", ".json", ".csv", ".log", ".c", ".cpp", ".h", ".sh"}
_SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", ".cache", "snap"}

def search_and_display(query: str) -> str:
    cleaned_query = query.lower().replace("search for", "").replace("find file", "").replace("open file", "").replace("in files", "").strip()
    if not cleaned_query:
        return "Please specify the filename to search for."

    matches = []
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(FILE_SEARCH_ROOT):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            scanned += 1
            if scanned > 30000:
                break
            if cleaned_query in fname.lower():
                matches.append(os.path.join(dirpath, fname))
        if scanned > 30000:
            break

    if not matches:
        return f"No files matching '{cleaned_query}' were found under {FILE_SEARCH_ROOT}."

    matches.sort(key=len)
    target = matches[0]
    filename = os.path.basename(target)
    ext = os.path.splitext(target)[1].lower()

    # Open file using native desktop launcher
    try:
        subprocess.Popen(["xdg-open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    if ext in _TEXT_EXTS:
        try:
            with open(target, "r", errors="ignore") as f:
                content = f.read(500).strip().replace("\n", " ")
            return f"Found and opened {filename}. Content preview: {content}..."
        except Exception:
            pass

    return f"Located and opened {filename} at {target}."
