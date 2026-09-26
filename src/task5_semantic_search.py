"""
Task 5 — Semantic search.

Embed query bằng chính hàm của Task 4, query ChromaDB và đổi cosine distance
thành similarity. Output phải theo SearchResult, sort giảm dần và không quá top_k.
"""

from .task4_chunking_indexing import embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về dense SearchResult theo score giảm dần."""
    if not query.strip():
        return []

    query_vector = embed_texts([query])[0]
    collection = get_collection()

    response = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    if not response or not response.get("ids") or not response["ids"][0]:
        return []

    results = []
    seen_ids = set()

    for item_id, content, metadata, distance in zip(
        response["ids"][0],
        response["documents"][0],
        response["metadatas"][0],
        response["distances"][0],
    ):
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)

        # Truy vấn ChromaDB trả về distance (cosine distance: 0 = giống hệt, 2 = ngược hoàn toàn)
        # Similarity score = 1 - distance
        score = float(max(0.0, 1.0 - distance))

        # Restore url if empty string
        meta_dict = dict(metadata) if metadata else {}
        if meta_dict.get("url") == "":
            meta_dict["url"] = None

        results.append(
            {
                "id": item_id,
                "content": content,
                "score": score,
                "metadata": meta_dict,
                "retrieval_method": "dense",
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
        res = semantic_search(q, top_k=3)
        for idx, item in enumerate(res, 1):
            print(f"  {idx}. [Score: {item['score']:.4f}] ID: {item['id']}")
            print(f"     Title: {item['metadata'].get('title')}")
            print(f"     Snippet: {item['content'][:100].strip()}...\n")

