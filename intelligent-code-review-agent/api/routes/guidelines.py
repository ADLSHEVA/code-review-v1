"""Guidelines upload and management API routes."""

import os
import re
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from ..models import GuidelineFile, GuidelineListResponse, GuidelineUploadResponse, ReindexResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy imports to avoid loading heavy ML libs at import time
_settings = None
_indexer = None


def _get_settings():
    global _settings
    if _settings is None:
        import sys
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))
        from src.config import settings
        _settings = settings
    return _settings


def _get_indexer():
    global _indexer
    if _indexer is None:
        import sys
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))
        from src.rag.indexer import GuidelineIndexer
        _indexer = GuidelineIndexer()
    return _indexer


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    name = Path(filename).name
    if not name or name.startswith(".") or ".." in name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not re.match(r'^[\w\-. ]+$', name):
        raise HTTPException(status_code=400, detail="Filename contains invalid characters")
    return name


def _get_upload_dir() -> Path:
    settings = _get_settings()
    upload_dir = settings.custom_guidelines_path
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


@router.post("/upload", response_model=GuidelineUploadResponse)
async def upload_guideline(file: UploadFile = File(...)):
    """Upload a guideline document and index it into the vector store."""
    settings = _get_settings()
    indexer = _get_indexer()

    # Validate filename
    filename = _sanitize_filename(file.filename or "unnamed")

    # Validate extension
    ext = Path(filename).suffix.lower()
    if ext not in settings.allowed_upload_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}. Allowed: {', '.join(settings.allowed_upload_extensions)}"
        )

    # Read file content
    content = await file.read()

    # Validate size
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb} MB"
        )

    # Save file
    upload_dir = _get_upload_dir()
    file_path = upload_dir / filename
    source_path = str(file_path.resolve())

    # If file already exists, delete old ChromaDB entries
    if file_path.exists():
        indexer.delete_by_source(source_path)

    file_path.write_bytes(content)

    # Load and index
    import sys
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    from src.rag.document_loader import DocumentLoader

    docs = DocumentLoader.load_single_file(str(file_path), doc_type="custom_guideline")
    if not docs:
        # Clean up empty file
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Could not extract any text from the file")

    # Normalize source paths in metadata
    for doc in docs:
        doc.metadata["source"] = source_path

    chunks_indexed = indexer.index_documents(docs)

    return GuidelineUploadResponse(
        filename=filename,
        size_bytes=len(content),
        chunks_indexed=chunks_indexed,
        message=f"Uploaded and indexed {chunks_indexed} chunks",
    )


@router.get("/list", response_model=GuidelineListResponse)
async def list_guidelines():
    """List all uploaded guideline files."""
    upload_dir = _get_upload_dir()
    indexer = _get_indexer()

    files = []
    for f in sorted(upload_dir.iterdir()):
        if f.is_file():
            stat = f.stat()
            # Count docs from this source by checking ChromaDB
            try:
                results = indexer.vectorstore.similarity_search(
                    "", k=1000, filter={"source": str(f.resolve())}
                )
                doc_count = len(results)
            except Exception:
                doc_count = 0

            files.append(GuidelineFile(
                filename=f.name,
                size_bytes=stat.st_size,
                uploaded_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                doc_count=doc_count,
            ))

    total_chunks = indexer.count()

    return GuidelineListResponse(
        files=files,
        total_files=len(files),
        total_chunks=total_chunks,
    )


@router.delete("/{filename}")
async def delete_guideline(filename: str):
    """Delete an uploaded guideline file and its indexed chunks."""
    safe_name = _sanitize_filename(filename)
    upload_dir = _get_upload_dir()
    file_path = upload_dir / safe_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    source_path = str(file_path.resolve())

    # Delete from ChromaDB
    indexer = _get_indexer()
    indexer.delete_by_source(source_path)

    # Delete file
    file_path.unlink()

    return {"message": "deleted", "filename": safe_name}


@router.post("/reindex", response_model=ReindexResponse)
async def reindex_guidelines():
    """Re-index all uploaded guideline documents."""
    settings = _get_settings()
    indexer = _get_indexer()
    upload_dir = _get_upload_dir()

    import sys
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    from src.rag.document_loader import DocumentLoader

    # Clear existing custom guidelines from vector store
    indexer.delete_by_doc_type("custom_guideline")

    # Re-index all files
    all_docs = []
    files_processed = 0

    for f in upload_dir.iterdir():
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext not in settings.allowed_upload_extensions:
            continue

        docs = DocumentLoader.load_single_file(str(f), doc_type="custom_guideline")
        for doc in docs:
            doc.metadata["source"] = str(f.resolve())
        all_docs.extend(docs)
        files_processed += 1

    chunks_indexed = 0
    if all_docs:
        chunks_indexed = indexer.index_documents(all_docs)

    return ReindexResponse(
        files_processed=files_processed,
        chunks_indexed=chunks_indexed,
        message=f"Re-indexed {files_processed} files ({chunks_indexed} chunks)",
    )
