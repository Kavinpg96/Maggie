"""
rag.py - Offline Retrieval-Augmented Generation (lightweight version)

Feeds local PDFs / text files / markdown / code into a local TF-IDF
index using scikit-learn, so Maggie can answer questions about your
own documents with zero internet dependency and no heavy AI
libraries -- no PyTorch, no CUDA wheels, no ChromaDB. The whole index
lives in one small file (data/tfidf_index.joblib), typically a few
MB even for thousands of pages.

This is keyword/relevance matching (TF-IDF + cosine similarity), not
semantic embeddings -- it won't catch pure synonyms the way a neural
embedding model would, but for finding "which of my notes mentions
the R2000 project" it works well and installs in seconds instead of
gigabytes.

Usage from voice/brain:
    import rag
    hits = rag.query("what did the R2000 spec say about tolerances")
    # -> list of {"text": ..., "source": ..., "score": ...}

Ingestion (one-off or repeatable), either from code or via ingest.py:
    import rag
    rag.ingest_path("/home/kavin/Documents/project_notes")
"""
import os

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import RAG_CHUNK_OVERLAP, RAG_CHUNK_SIZE, RAG_TOP_K, TFIDF_INDEX_PATH

_TEXT_EXTS = {".txt", ".md", ".markdown", ".py", ".json", ".csv", ".log", ".c", ".cpp", ".h", ".sh", ".rst"}
_PDF_EXTS = {".pdf"}
_SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", ".cache", "snap"}

_EMPTY_INDEX = {"chunks": [], "sources": [], "vectorizer": None, "matrix": None}


def _load_index() -> dict:
    if os.path.exists(TFIDF_INDEX_PATH):
        try:
            return joblib.load(TFIDF_INDEX_PATH)
        except Exception:
            pass
    return dict(_EMPTY_INDEX)


def _save_index(index: dict):
    os.makedirs(os.path.dirname(TFIDF_INDEX_PATH), exist_ok=True)
    joblib.dump(index, TFIDF_INDEX_PATH)


def _rebuild_vectorizer(index: dict):
    """TF-IDF needs to see the whole corpus to build its vocabulary, so
    this refits over all chunks whenever new documents are added. Fine
    for a personal knowledge base (thousands of chunks, not millions)."""
    if not index["chunks"]:
        index["vectorizer"] = None
        index["matrix"] = None
        return
    vectorizer = TfidfVectorizer(stop_words="english", max_features=50000)
    matrix = vectorizer.fit_transform(index["chunks"])
    index["vectorizer"] = vectorizer
    index["matrix"] = matrix


def _extract_text(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in _TEXT_EXTS:
        with open(path, "r", errors="ignore") as f:
            return f.read()
    if ext in _PDF_EXTS:
        try:
            from pypdf import PdfReader
            reader = PdfReader(path)
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception:
            return ""
    return ""


def _chunk_text(text: str, chunk_size: int = RAG_CHUNK_SIZE, overlap: int = RAG_CHUNK_OVERLAP):
    text = " ".join(text.split())
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def ingest_file(path: str) -> int:
    """Ingest a single file. Returns number of chunks added."""
    text = _extract_text(path)
    chunks = _chunk_text(text)
    if not chunks:
        return 0

    index = _load_index()

    # Drop any existing chunks from this same file first (re-ingest = replace)
    keep = [(c, s) for c, s in zip(index["chunks"], index["sources"]) if s != path]
    index["chunks"] = [c for c, _ in keep] + chunks
    index["sources"] = [s for _, s in keep] + [path] * len(chunks)

    _rebuild_vectorizer(index)
    _save_index(index)
    return len(chunks)


def ingest_path(root: str) -> dict:
    """Ingest a single file or walk a directory, ingesting every supported file.
    Returns {"files": N, "chunks": N}. Rebuilds the index once at the end
    rather than after every file, so bulk folders ingest quickly."""
    root = os.path.expanduser(root)
    index = _load_index()
    files_done = 0
    chunks_done = 0

    def _ingest_into(path):
        nonlocal files_done, chunks_done
        text = _extract_text(path)
        chunks = _chunk_text(text)
        if not chunks:
            return
        keep = [(c, s) for c, s in zip(index["chunks"], index["sources"]) if s != path]
        index["chunks"] = [c for c, _ in keep] + chunks
        index["sources"] = [s for _, s in keep] + [path] * len(chunks)
        files_done += 1
        chunks_done += len(chunks)

    if os.path.isfile(root):
        _ingest_into(root)
    else:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in _TEXT_EXTS and ext not in _PDF_EXTS:
                    continue
                try:
                    _ingest_into(os.path.join(dirpath, fname))
                except Exception:
                    continue

    _rebuild_vectorizer(index)
    _save_index(index)
    return {"files": files_done, "chunks": chunks_done}


def query(question: str, top_k: int = RAG_TOP_K):
    """Return the top_k most relevant chunks for a question.
    Each result: {"text": str, "source": str, "score": float (higher = closer)}.
    Returns [] if the knowledge base is empty."""
    index = _load_index()
    if not index["chunks"] or index["vectorizer"] is None:
        return []

    q_vec = index["vectorizer"].transform([question])
    sims = cosine_similarity(q_vec, index["matrix"])[0]

    ranked = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:top_k]
    hits = []
    for i in ranked:
        if sims[i] <= 0:
            continue
        hits.append({"text": index["chunks"][i], "source": index["sources"][i], "score": float(sims[i])})
    return hits


def build_context_block(question: str, top_k: int = RAG_TOP_K) -> str:
    """Convenience helper: turns query() results into a single
    prompt-ready context string, or "" if nothing relevant was found."""
    hits = query(question, top_k=top_k)
    if not hits:
        return ""
    parts = [f"[Source: {os.path.basename(h['source'])}]\n{h['text']}" for h in hits]
    return "\n\n".join(parts)


def get_index_size() -> int:
    """Returns how many chunks are currently indexed."""
    return len(_load_index()["chunks"])


def get_indexed_sources() -> list:
    """Returns the unique file basenames currently in the index."""
    index = _load_index()
    seen, out = set(), []
    for s in index["sources"]:
        name = os.path.basename(s)
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out
