"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""

import re
import unicodedata
from typing import Any

from .task4_chunking_indexing import chunk_documents, load_documents

CORPUS: list[dict] = []
_BM25_INDEX: Any = None
_CACHED_CORPUS_REF: Any = None


def tokenize_text(text: str) -> list[str]:
    """Tokenizer: lowercase, NFC normalization, giữ dấu tiếng Việt và số/ký hiệu (vd '6.5', 'Task 1')."""
    if not text:
        return []
    text_norm = unicodedata.normalize("NFC", text).lower()
    # Tìm các từ bao gồm chữ cái Unicode, chữ số, và dấu chấm nằm giữa các chữ số (vd 6.5)
    tokens = re.findall(r"\b[\w\.\-]+?\b", text_norm)
    return [t for t in tokens if t.strip()]


def get_corpus() -> list[dict]:
    """Tải và cache danh sách chunks từ Task 4 nếu CORPUS module rỗng."""
    global CORPUS
    if not CORPUS:
        docs = load_documents()
        CORPUS = chunk_documents(docs)
    return CORPUS


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4 (dùng BM25Plus để hỗ trợ corpus nhỏ)."""
    try:
        from rank_bm25 import BM25Plus

        bm25_cls = BM25Plus
    except ImportError:
        from rank_bm25 import BM25Okapi

        bm25_cls = BM25Okapi

    tokenized_corpus = [tokenize_text(item["content"]) for item in corpus]
    return bm25_cls(tokenized_corpus)


def get_bm25_index(corpus: list[dict]):
    """Khởi tạo hoặc cập nhật BM25 index khi corpus thay đổi (vd khi test monkeypatch)."""
    global _BM25_INDEX, _CACHED_CORPUS_REF
    corpus_ref = (id(corpus), len(corpus), corpus[0]["id"] if corpus else None)
    if _BM25_INDEX is None or _CACHED_CORPUS_REF != corpus_ref:
        _BM25_INDEX = build_bm25_index(corpus)
        _CACHED_CORPUS_REF = corpus_ref
    return _BM25_INDEX


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    if not query.strip():
        return []

    corpus = get_corpus()
    if not corpus:
        return []

    bm25 = get_bm25_index(corpus)
    query_tokens = tokenize_text(query)
    if not query_tokens:
        return []

    scores = bm25.get_scores(query_tokens)
    query_token_set = set(query_tokens)

    results = []
    seen_ids = set()

    for idx, score in enumerate(scores):
        item = corpus[idx]
        item_id = item["id"]
        if item_id in seen_ids:
            continue

        doc_tokens = set(tokenize_text(item["content"]))
        matching_tokens = query_token_set & doc_tokens

        # Lọc bỏ kết quả score <= 0 trừ khi có ít nhất 1 query token khớp thực sự
        if score <= 0 and not matching_tokens:
            continue

        seen_ids.add(item_id)

        effective_score = float(score)
        if effective_score <= 0 and matching_tokens:
            effective_score = float(len(matching_tokens) * 0.1)

        meta_dict = dict(item["metadata"]) if item.get("metadata") else {}
        if meta_dict.get("url") == "":
            meta_dict["url"] = None

        results.append(
            {
                "id": item_id,
                "content": item["content"],
                "score": effective_score,
                "metadata": meta_dict,
                "retrieval_method": "bm25",
            }
        )

    # Sort score giảm dần
    sorted_results = sorted(results, key=lambda item: item["score"], reverse=True)
    return sorted_results[:top_k]


if __name__ == "__main__":
    test_queries = [
        "Chính sách hủy và đổi ngày thi IELTS",  # Tiếng Việt
        "IELTS Writing Task 1 band descriptors and criteria",  # Tiếng Anh
        "Task Achievement",  # Tên riêng / thuật ngữ
    ]

    for q in test_queries:
        print(f"=== Query: '{q}' ===")
        res = lexical_search(q, top_k=3)
        for idx, item in enumerate(res, 1):
            print(f"  {idx}. [Score: {item['score']:.4f}] ID: {item['id']}")
            print(f"     Title: {item['metadata'].get('title')}")
            print(f"     Snippet: {item['content'][:100].strip()}...\n")


