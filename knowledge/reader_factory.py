"""Reader factory — 构建文档读取器。"""

from agno.knowledge.chunking.fixed import FixedSizeChunking
from agno.knowledge.chunking.semantic import SemanticChunking
from agno.knowledge.reader.base import Reader
from agno.knowledge.reader.text_reader import TextReader
from agno.knowledge.reader.pdf_reader import PDFReader
from agno.knowledge.reader.docx_reader import DocxReader

from config.settings import settings

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".md", ".txt", ".html"}


def _build_chunking_strategy():
    if settings.CHUNKING_STRATEGY == "semantic":
        return SemanticChunking(
            chunk_size=settings.CHUNK_SIZE,
            similarity_threshold=settings.SEMANTIC_SIMILARITY_THRESHOLD,
        )
    return FixedSizeChunking(
        chunk_size=settings.CHUNK_SIZE,
        overlap=settings.CHUNK_OVERLAP,
    )


def build_reader(file_ext: str) -> Reader:
    chunking = _build_chunking_strategy()
    ext = file_ext.lower()

    if ext == ".pdf":
        reader = PDFReader(chunking_strategy=chunking)
    elif ext == ".docx":
        reader = DocxReader(chunking_strategy=chunking)
    elif ext in (".md", ".txt", ".html"):
        reader = TextReader(chunking_strategy=chunking)
    else:
        reader = TextReader(chunking_strategy=chunking)

    return reader
