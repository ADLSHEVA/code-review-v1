"""Vector store indexing for project documentation and guidelines."""

import logging
import os

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from ..config import settings
from .document_loader import DocumentLoader

logger = logging.getLogger(__name__)


class GuidelineIndexer:
    """Indexes project documents and guidelines into a vector store."""

    # Class-level singletons to avoid reloading embeddings per instance
    _shared_embeddings = None
    _shared_vectorstores: dict[str, Chroma] = {}

    def __init__(self, persist_dir: str | None = None):
        self.persist_dir = persist_dir or settings.vectorstore_dir

    @property
    def embeddings(self):
        if GuidelineIndexer._shared_embeddings is None:
            try:
                from langchain_community.embeddings import HuggingFaceEmbeddings
                GuidelineIndexer._shared_embeddings = HuggingFaceEmbeddings(
                    model_name=settings.embedding_model
                )
            except ImportError:
                logger.warning(
                    "HuggingFace embeddings not available. "
                    "Install sentence-transformers for RAG support."
                )
                raise
        return GuidelineIndexer._shared_embeddings

    @property
    def vectorstore(self):
        if self.persist_dir not in GuidelineIndexer._shared_vectorstores:
            os.makedirs(self.persist_dir, exist_ok=True)
            GuidelineIndexer._shared_vectorstores[self.persist_dir] = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings,
            )
        return GuidelineIndexer._shared_vectorstores[self.persist_dir]

    def index_project(self, project_path: str) -> int:
        """Index all relevant docs from a project. Returns count of indexed documents."""
        docs = DocumentLoader.load_directory(project_path)
        if not docs:
            logger.info(f"No documents found to index in {project_path}")
            return 0

        self.vectorstore.add_documents(docs)
        logger.info(f"Indexed {len(docs)} document chunks from {project_path}")
        return len(docs)

    def index_guidelines(self, guidelines_dir: str | None = None) -> int:
        """Index the default guidelines from data/guidelines/."""
        dir_path = guidelines_dir or str(settings.guidelines_dir)
        if not os.path.isdir(dir_path):
            logger.warning(f"Guidelines directory not found: {dir_path}")
            return 0

        docs = DocumentLoader.load_directory(dir_path)
        if not docs:
            return 0

        self.vectorstore.add_documents(docs)
        logger.info(f"Indexed {len(docs)} guideline chunks from {dir_path}")
        return len(docs)

    def index_documents(self, documents: list[Document]) -> int:
        """Index a list of pre-loaded documents."""
        if not documents:
            return 0
        self.vectorstore.add_documents(documents)
        return len(documents)

    def clear(self):
        """Clear all indexed documents."""
        if self.persist_dir in GuidelineIndexer._shared_vectorstores:
            GuidelineIndexer._shared_vectorstores[self.persist_dir].delete_collection()
            del GuidelineIndexer._shared_vectorstores[self.persist_dir]

    def delete_by_source(self, source_path: str):
        """Delete all document chunks from a specific source file."""
        try:
            self.vectorstore.delete(where={"source": source_path})
        except Exception:
            logger.warning(f"Failed to delete by source: {source_path}")

    def delete_by_doc_type(self, doc_type: str):
        """Delete all document chunks of a specific doc type."""
        try:
            self.vectorstore.delete(where={"doc_type": doc_type})
        except Exception:
            logger.warning(f"Failed to delete by doc_type: {doc_type}")

    def count(self) -> int:
        """Return total number of indexed document chunks."""
        try:
            return self.vectorstore._collection.count()
        except Exception:
            return 0
