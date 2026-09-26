"""
Task 4 — Chunking, embedding và indexing.

Hướng dẫn:
    1. Đọc toàn bộ Markdown trong data/standardized/.
    2. Chia văn bản bằng strategy đã chọn.
    3. Embed chunks bằng một provider duy nhất.
    4. Upsert vào ChromaDB với cosine distance.

Mỗi document/chunk phải theo docs/MODULE_CONTRACTS.md. ID cần ổn định để
chạy lại pipeline không tạo dữ liệu trùng. Task 5 phải dùng chung embed_texts().
"""

import re
from pathlib import Path
from typing import Any

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Cấu hình tham số chunking
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024

COLLECTION_NAME = "rag_documents"

_MODEL_INSTANCE: Any = None


def get_embedding_model() -> Any:
    """Khởi tạo và cache model SentenceTransformer 1 lần duy nhất."""
    global _MODEL_INSTANCE
    if _MODEL_INSTANCE is None:
        from sentence_transformers import SentenceTransformer

        _MODEL_INSTANCE = SentenceTransformer(EMBEDDING_MODEL)
    return _MODEL_INSTANCE


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Tạo vector embeddings cho danh sách văn bản (dùng chung Task 4 & Task 5)."""
    if not texts:
        return []
    model = get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=False).tolist()
    return embeddings


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def extract_title(content: str, default_title: str) -> str:
    """Trích xuất heading đầu tiên (# Title) làm title nếu có."""
    for line in content.splitlines():
        line_strip = line.strip()
        if line_strip.startswith("#"):
            title_text = re.sub(r"^#+\s*", "", line_strip).strip()
            if title_text:
                return title_text
    return default_title


def load_documents() -> list[dict]:
    """Đọc mọi file .md trong data/standardized/ -> Document(id, content, metadata)."""
    documents = []
    if not STANDARDIZED_DIR.exists():
        return documents

    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        rel_path = path.relative_to(STANDARDIZED_DIR)
        doc_id = rel_path.with_suffix("").as_posix()
        doc_type = "legal" if "legal" in rel_path.parts else "news"
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            continue

        title = extract_title(content, path.stem)
        documents.append(
            {
                "id": doc_id,
                "content": content,
                "metadata": {
                    "source": rel_path.as_posix(),
                    "title": title,
                    "doc_type": doc_type,
                    "url": None,
                },
            }
        )
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks bằng RecursiveCharacterTextSplitter."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n# ", "\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for doc in documents:
        raw_chunks = splitter.split_text(doc["content"])
        chunk_idx = 0
        for text in raw_chunks:
            text_clean = text.strip()
            if not text_clean:
                continue

            chunk_id = f"{doc['id']}::chunk_{chunk_idx}"
            chunks.append(
                {
                    "id": chunk_id,
                    "content": text_clean,
                    "metadata": {
                        **doc["metadata"],
                        "chunk_index": chunk_idx,
                    },
                }
            )
            chunk_idx += 1
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm vector embedding vào từng chunk."""
    if not chunks:
        return []
    texts = [chunk["content"] for chunk in chunks]
    vectors = embed_texts(texts)
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    return chunks


def sanitize_metadata_for_chroma(metadata: dict) -> dict:
    """Chỉ giữ lại các kiểu dữ liệu phẳng (str, int, float, bool) cho ChromaDB."""
    sanitized = {}
    for k, v in metadata.items():
        if isinstance(v, (str, int, float, bool)):
            sanitized[k] = v
        elif v is None:
            sanitized[k] = ""
        else:
            sanitized[k] = str(v)
    return sanitized


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB (id ổn định, chạy lại không nhân bản)."""
    if not chunks:
        return
    collection = get_collection()

    ids = [chunk["id"] for chunk in chunks]
    documents = [chunk["content"] for chunk in chunks]
    embeddings = [chunk["embedding"] for chunk in chunks]
    metadatas = [sanitize_metadata_for_chroma(chunk["metadata"]) for chunk in chunks]

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)

    collection = get_collection()
    record_count = collection.count()

    print(f"Loaded documents: {len(documents)}")
    print(f"Generated chunks: {len(chunks)}")
    print(f"Collection records: {record_count}")

    print("\nSample chunk metadatas (up to 3):")
    for sample in chunks[:3]:
        print(f"ID: {sample['id']}")
        print(f"Metadata: {sample['metadata']}\n")


if __name__ == "__main__":
    run_pipeline()

