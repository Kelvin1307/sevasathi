from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CSV = BASE_DIR / "updated_data.csv"
DEFAULT_GOV_DIR = BASE_DIR / "gov_myscheme"
DEFAULT_INDEX_DIR = BASE_DIR / "cache" / "faiss_index"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SCHEMA_VERSION = 1
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120

# All Indian states and UTs for state-tagging scheme documents
INDIAN_STATES_FOR_TAGGING = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal", "Delhi", "Jammu", "Kashmir", "Ladakh", "Puducherry",
    "Chandigarh", "Andaman", "Nicobar", "Lakshadweep", "Andaman and Nicobar",
    "Dadra", "Daman", "Diu",
]


def extract_state_from_text(*texts: str) -> str:
    """Scan one or more text fields for a known Indian state/UT name.

    Returns the matched state name, or ``'India'`` for central/national schemes.
    """
    combined = " ".join(str(t) for t in texts if t).lower()
    for state in INDIAN_STATES_FOR_TAGGING:
        if state.lower() in combined:
            return state
    return "India"


def number_from_text(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).lower().replace(",", "")
    digits = "".join(char if char.isdigit() or char == "." else " " for char in text).split()
    return float(digits[0]) if digits else None


def normalize_metadata(values: dict[str, Any], source: str, file_name: str = "") -> dict[str, Any]:
    normalized = {key.lower().strip().replace(" ", "_"): value for key, value in values.items()}
    scheme_name = str(normalized.get("scheme_name", normalized.get("name", "Unknown")))
    category_text = f"{scheme_name} {normalized.get('category', '')} {normalized.get('target_category', '')}".lower()
    gender = "women" if any(word in category_text for word in ("women", "female", "mahila")) else "any"
    social_category = "SC" if "scheduled caste" in category_text or " sc" in f" {category_text}" else "any"
    loan_type = "education" if "education" in category_text or "student" in category_text else "business"
    if "micro" in category_text:
        max_loan = 140000
    elif "term loan" in category_text:
        max_loan = 5000000
    elif "educational" in category_text:
        max_loan = 3000000
    else:
        max_loan = number_from_text(normalized.get("max_loan"))

    # Prefer an explicit 'state'/'location' column; otherwise extract from
    # scheme_name and tags so that state-specific schemes are properly tagged.
    raw_state = normalized.get("state") or normalized.get("location") or ""
    if raw_state and str(raw_state).strip().lower() not in ("", "nan", "none", "india", "all india", "national"):
        state = str(raw_state).strip()
    else:
        state = extract_state_from_text(
            scheme_name,
            normalized.get("tags", ""),
            file_name,
        )
    return {
        "source": source,
        "file_name": file_name,
        "scheme_name": scheme_name,
        "state": state,
        "social_category": social_category,
        "gender": gender,
        "income_limit": number_from_text(normalized.get("income_limit")) or 500000,
        "loan_type": loan_type,
        "max_loan": max_loan,
    }


def load_csv_documents(csv_path: Path) -> list[Document]:
    frame = pd.read_csv(csv_path)
    documents = []
    for _, row in frame.iterrows():
        values = {str(column): row[column] for column in frame.columns if pd.notna(row[column])}
        content = "\n".join(f"{key}: {value}" for key, value in values.items())
        documents.append(Document(page_content=content, metadata=normalize_metadata(values, "csv")))
    return documents


def load_text_documents(gov_dir: Path) -> list[Document]:
    documents = []
    for path in gov_dir.rglob("*") if gov_dir.exists() else []:
        if not path.is_file() or path.suffix.lower() not in {".txt", ".md", ".json", ".csv"}:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        if content.strip():
            documents.append(Document(
                page_content=content,
                metadata=normalize_metadata({}, str(path), path.name),
            ))
    return documents


def load_pdf_documents(gov_dir: Path) -> list[Document]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return []

    documents = []
    seen_names: set[str] = set()
    for path in gov_dir.rglob("*.pdf") if gov_dir.exists() else []:
        canonical = path.stem.replace(" copy", "").strip()
        if canonical in seen_names:
            continue
        seen_names.add(canonical)
        try:
            content = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        except Exception:
            continue
        if content.strip():
            documents.append(Document(
                page_content=content,
                metadata=normalize_metadata({"scheme_name": canonical}, str(path), path.name),
            ))
    return documents


def source_hashes(csv_path: Path, gov_dir: Path) -> dict[str, str]:
    paths = [csv_path]
    paths.extend(path for path in gov_dir.rglob("*") if path.is_file())
    hashes = {}
    for path in sorted(paths):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[str(path.relative_to(BASE_DIR))] = digest
    return hashes


def build_index(csv_path: Path, gov_dir: Path, index_dir: Path) -> None:
    documents = load_csv_documents(csv_path) + load_text_documents(gov_dir) + load_pdf_documents(gov_dir)
    if not documents:
        raise RuntimeError("No source documents were found; refusing to create an empty index.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vectorstore = FAISS.from_documents(chunks, embeddings)

    index_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary_dir = Path(tempfile.mkdtemp(prefix="faiss-build-", dir=index_dir.parent))
    try:
        vectorstore.save_local(str(temporary_dir))
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "embedding_model": EMBEDDING_MODEL,
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
            "document_count": len(documents),
            "chunk_count": len(chunks),
            "built_at": datetime.now(timezone.utc).isoformat(),
            "source_hashes": source_hashes(csv_path, gov_dir),
        }
        (temporary_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        backup_dir = index_dir.with_name(f"{index_dir.name}.previous")
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        if index_dir.exists():
            index_dir.replace(backup_dir)
        temporary_dir.replace(index_dir)
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
    except Exception:
        shutil.rmtree(temporary_dir, ignore_errors=True)
        raise

    print(f"Built {len(chunks)} chunks from {len(documents)} documents at {index_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the offline NyayaSetu FAISS knowledge artifact.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--gov-dir", type=Path, default=DEFAULT_GOV_DIR)
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    args = parser.parse_args()
    build_index(args.csv, args.gov_dir, args.index_dir)


if __name__ == "__main__":
    main()
