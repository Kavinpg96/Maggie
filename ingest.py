"""
ingest.py - CLI for feeding documents into Maggie's offline knowledge base.

Usage:
    python ingest.py ~/Documents/project_notes
    python ingest.py ~/Books/manual.pdf
    python ingest.py ~/notes ~/reports/q3.pdf   # multiple paths at once

The first run downloads a small local embedding model (~90MB, one-time,
needs internet). After that, ingestion and querying are fully offline.
"""
import sys

import rag


def main():
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <file_or_folder> [more paths...]")
        sys.exit(1)

    total_files = 0
    total_chunks = 0

    for path in sys.argv[1:]:
        print(f"Ingesting: {path} ...")
        result = rag.ingest_path(path)
        print(f"  -> {result['files']} file(s), {result['chunks']} chunk(s)")
        total_files += result["files"]
        total_chunks += result["chunks"]

    print(f"\nDone. Indexed {total_files} file(s), {total_chunks} chunk(s) total.")
    print("Try asking Maggie something like: \"Maggie, what do my notes say about X\"")


if __name__ == "__main__":
    main()
