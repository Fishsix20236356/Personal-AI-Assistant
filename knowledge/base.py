"""Knowledge base — 使用 LanceDB 本地向量存储（替代 PostgreSQL + pgvector）。"""

from functools import lru_cache

from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.lancedb import LanceDb

from config.settings import settings


@lru_cache(maxsize=1)
def get_shared_knowledge() -> Knowledge:
    embedder = OpenAIEmbedder(
        id=settings.EMBED_MODEL,
        api_key=settings.EMBED_API_KEY or None,
        base_url=settings.EMBED_BASE_URL or None,
        dimensions=settings.EMBED_DIMENSIONS,
    )

    vector_db = LanceDb(
        uri=settings.VECTOR_DB_PATH,
        table_name="knowledge_vectors",
        embedder=embedder,
    )

    return Knowledge(
        vector_db=vector_db,
        max_results=settings.KNOWLEDGE_MAX_RESULTS,
    )
