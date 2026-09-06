from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INDEX_DIR = BASE_DIR / "cache" / "faiss_index"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CACHE_SCHEMA_VERSION = 1

try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
except Exception:
    HuggingFaceEmbeddings = None


class KnowledgeIndexError(RuntimeError):
    """Raised when the offline knowledge artifact is unavailable or invalid."""


def load_manifest(index_dir: str | Path = DEFAULT_INDEX_DIR) -> dict[str, Any]:
    index_path = Path(index_dir)
    manifest_path = index_path / "manifest.json"
    if not manifest_path.exists():
        raise KnowledgeIndexError(
            f"Knowledge index manifest not found at {manifest_path}. "
            "Run python scripts/build_vectors.py first."
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KnowledgeIndexError(f"Could not read knowledge index manifest: {exc}") from exc

    required = {"schema_version", "embedding_model", "chunk_size", "chunk_overlap"}
    missing = required.difference(manifest)
    if missing:
        raise KnowledgeIndexError(f"Knowledge index manifest is missing: {', '.join(sorted(missing))}")
    if manifest["schema_version"] != CACHE_SCHEMA_VERSION:
        raise KnowledgeIndexError(
            f"Unsupported knowledge index schema {manifest['schema_version']}; expected {CACHE_SCHEMA_VERSION}. "
            "Rebuild the index."
        )
    if manifest["embedding_model"] != EMBEDDING_MODEL:
        raise KnowledgeIndexError(
            f"Knowledge index uses {manifest['embedding_model']}; expected {EMBEDDING_MODEL}. Rebuild the index."
        )
    return manifest


def load_vectorstore(index_dir: str | Path = DEFAULT_INDEX_DIR):
    """Load an existing FAISS artifact. This function never builds vectors."""
    index_path = Path(index_dir)
    load_manifest(index_path)
    if not (index_path / "index.faiss").exists() or not (index_path / "index.pkl").exists():
        raise KnowledgeIndexError(
            f"Knowledge index files are incomplete at {index_path}. Run python scripts/build_vectors.py first."
        )
    if HuggingFaceEmbeddings is None:
        raise KnowledgeIndexError("HuggingFaceEmbeddings is unavailable; install sentence-transformers.")

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    try:
        return FAISS.load_local(str(index_path), embeddings, allow_dangerous_deserialization=True)
    except Exception as exc:
        raise KnowledgeIndexError(f"Could not load FAISS knowledge index: {exc}") from exc


def _metadata_matches(metadata: dict[str, Any], profile: dict[str, Any]) -> bool:
    """Reject explicit metadata conflicts while allowing generic documents."""
    profile_state = str(profile.get("state", "")).strip().lower()
    document_state = str(metadata.get("state", "")).strip().lower()
    if profile_state and document_state and document_state not in {"india", "all india", "national", profile_state}:
        return False

    category = str(profile.get("category", profile.get("social_category", ""))).strip().lower()
    required_category = str(metadata.get("social_category", "")).strip().lower()
    if required_category and required_category not in {"general", "all", "any", category}:
        return False

    gender = str(profile.get("gender", "")).strip().lower()
    required_gender = str(metadata.get("gender", "")).strip().lower()
    if required_gender and required_gender not in {"any", "all", gender}:
        return False

    income = profile.get("income") or profile.get("annual_income") or profile.get("income_amount")
    income_limit = metadata.get("income_limit")
    if income is not None and income_limit is not None:
        try:
            if float(income) > float(income_limit):
                return False
        except (TypeError, ValueError):
            pass
    return True


def retrieve_documents(
    vectorstore,
    query: str,
    profile: dict[str, Any] | None = None,
    top_k: int = 8,
) -> list[Document]:
    """Filter retrieved FAISS documents by explicit metadata before returning them."""
    profile = profile or {}
    candidate_count = max(top_k * 8, 40)
    try:
        candidates = vectorstore.similarity_search(
            query,
            k=candidate_count,
            filter=lambda metadata: _metadata_matches(metadata or {}, profile),
        )
    except Exception as exc:
        raise KnowledgeIndexError(f"Knowledge retrieval failed: {exc}") from exc
    return candidates[:top_k]
