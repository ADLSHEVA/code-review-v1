"""Retrieve relevant guidelines from the vector store."""

import logging

from langchain_core.documents import Document

from ..config import settings
from .indexer import GuidelineIndexer

logger = logging.getLogger(__name__)


class GuidelineRetriever:
    """Retrieves relevant coding guidelines for review context."""

    def __init__(self, persist_dir: str | None = None):
        self.indexer = GuidelineIndexer(persist_dir)

    def search(self, query: str, k: int = 5) -> list[Document]:
        """Search for relevant guidelines."""
        try:
            return self.indexer.vectorstore.similarity_search(query, k=k)
        except Exception as e:
            logger.debug(f"RAG search failed (vectorstore may be empty): {e}")
            return []

    def search_with_scores(self, query: str, k: int = 5) -> list[tuple[Document, float]]:
        """Search with relevance scores."""
        try:
            return self.indexer.vectorstore.similarity_search_with_relevance_scores(
                query, k=k
            )
        except Exception as e:
            logger.debug(f"RAG search failed: {e}")
            return []

    def ensure_guidelines_indexed(self) -> bool:
        """Make sure default guidelines are indexed. Returns True if successful."""
        try:
            # Check if vectorstore has documents via public API
            results = self.indexer.vectorstore.similarity_search("", k=1)
            if results:
                return True

            # Index default guidelines
            count = self.indexer.index_guidelines()
            return count > 0
        except Exception as e:
            logger.warning(f"Failed to ensure guidelines indexed: {e}")
            return False
