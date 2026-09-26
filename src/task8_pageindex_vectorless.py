"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash.
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CACHE_FILE = Path(__file__).parent.parent / "data" / "pageindex_doc_ids.json"
PDF_CACHE_DIR = Path(__file__).parent.parent / "data" / "pageindex_pdfs"
REQUEST_TIMEOUT = float(os.getenv("PAGEINDEX_TIMEOUT", "30"))


def _get_client():
    if not PAGEINDEX_API_KEY.strip():
        raise RuntimeError("PAGEINDEX_API_KEY is not configured")
    from pageindex import PageIndexClient

    return PageIndexClient(api_key=PAGEINDEX_API_KEY.strip())


def _load_cache() -> dict[str, dict[str, Any]]:
    if not CACHE_FILE.exists():
        return {}
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_cache(cache: dict[str, dict[str, Any]]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = CACHE_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(CACHE_FILE)


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _unicode_font() -> Path | None:
    windir = Path(os.getenv("WINDIR", r"C:\Windows"))
    candidates = [
        windir / "Fonts" / "arial.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    return next((path for path in candidates if path.exists()), None)


def _markdown_to_pdf(markdown_path: Path, pdf_path: Path) -> None:
    """Create the PDF accepted by PageIndex while preserving Unicode text."""
    from fpdf import FPDF

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    font_path = _unicode_font()
    if font_path:
        pdf.add_font("DocumentFont", fname=str(font_path))
        pdf.set_font("DocumentFont", size=10)
        normalize = lambda value: value
    else:
        pdf.set_font("Helvetica", size=10)
        normalize = lambda value: value.encode("latin-1", "replace").decode("latin-1")

    for line in markdown_path.read_text(encoding="utf-8").splitlines():
        pdf.multi_cell(
            0,
            5,
            normalize(line) if line else " ",
            new_x="LMARGIN",
            new_y="NEXT",
        )
    pdf.output(str(pdf_path))


def _upload_path(markdown_path: Path) -> Path:
    """Reuse an original legal PDF when present; convert other Markdown."""
    relative = markdown_path.relative_to(STANDARDIZED_DIR)
    original = (
        Path(__file__).parent.parent
        / "data"
        / "landing"
        / relative.with_suffix(".pdf")
    )
    if original.exists():
        return original

    pdf_path = PDF_CACHE_DIR / relative.with_suffix(".pdf")
    if (
        not pdf_path.exists()
        or pdf_path.stat().st_mtime < markdown_path.stat().st_mtime
    ):
        _markdown_to_pdf(markdown_path, pdf_path)
    return pdf_path


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    if not STANDARDIZED_DIR.exists():
        return

    from .task4_chunking_indexing import extract_title

    client = _get_client()
    cache = _load_cache()
    for markdown_path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = markdown_path.read_text(encoding="utf-8").strip()
        if not content:
            continue
        relative = markdown_path.relative_to(STANDARDIZED_DIR)
        source = relative.as_posix()
        digest = _file_digest(markdown_path)
        cached = cache.get(source, {})
        if cached.get("doc_id") and cached.get("sha256") == digest:
            continue

        upload_path = _upload_path(markdown_path)
        response = client.submit_document(str(upload_path))
        if not isinstance(response, dict) or not response.get("doc_id"):
            raise RuntimeError(f"PageIndex returned no doc_id for {source}")
        cache[source] = {
            "doc_id": str(response["doc_id"]),
            "sha256": digest,
            "title": extract_title(content, markdown_path.stem),
            "doc_type": "legal" if "legal" in relative.parts else "news",
            "url": None,
        }
        # Persist each successful upload so a later failure does not lose IDs.
        _save_cache(cache)


def _wait_for_retrieval(client: Any, retrieval_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + max(REQUEST_TIMEOUT, 1.0)
    while True:
        response = client.get_retrieval(retrieval_id)
        if not isinstance(response, dict):
            raise RuntimeError("Invalid PageIndex retrieval response")
        status = str(response.get("status", "")).lower()
        if status == "completed" or response.get("retrieved_nodes") is not None:
            return response
        if status in {"failed", "error", "cancelled"}:
            raise RuntimeError(f"PageIndex retrieval ended with status={status}")
        if time.monotonic() >= deadline:
            raise TimeoutError("Timed out waiting for PageIndex retrieval")
        time.sleep(1.0)


def _node_content(node: Any) -> str:
    if isinstance(node, str):
        return node.strip()
    if not isinstance(node, dict):
        return ""
    for key in (
        "relevant_content",
        "text",
        "content",
        "node_text",
        "markdown",
        "summary",
    ):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    if top_k <= 0 or not query.strip():
        return []

    cache = _load_cache()
    if not cache:
        upload_documents()
        cache = _load_cache()
    if not cache:
        return []

    client = _get_client()
    results: list[dict] = []
    seen_ids: set[str] = set()
    for source, document in cache.items():
        doc_id = document.get("doc_id")
        if not isinstance(doc_id, str) or not doc_id:
            continue
        submitted = client.submit_query(doc_id=doc_id, query=query.strip())
        retrieval_id = submitted.get("retrieval_id") if isinstance(submitted, dict) else None
        if not retrieval_id:
            raise RuntimeError(f"PageIndex returned no retrieval_id for {source}")
        response = _wait_for_retrieval(client, str(retrieval_id))
        nodes = response.get("retrieved_nodes") or []
        if isinstance(nodes, dict):
            nodes = nodes.get("nodes") or nodes.get("results") or [nodes]
        if not isinstance(nodes, list):
            continue

        expanded_nodes: list[Any] = []
        for node in nodes:
            relevant_contents = (
                node.get("relevant_contents") if isinstance(node, dict) else None
            )
            if isinstance(relevant_contents, list) and relevant_contents:
                for content_index, relevant_content in enumerate(relevant_contents):
                    if isinstance(relevant_content, dict):
                        flattened = {**node, **relevant_content}
                    else:
                        flattened = {**node, "relevant_content": relevant_content}
                    flattened["id"] = (
                        f"{node.get('node_id') or node.get('id') or 'node'}"
                        f"::{content_index}"
                    )
                    expanded_nodes.append(flattened)
            else:
                expanded_nodes.append(node)

        for rank, node in enumerate(expanded_nodes, start=1):
            content = _node_content(node)
            if not content:
                continue
            node_data = node if isinstance(node, dict) else {}
            node_id = str(
                node_data.get("node_id")
                or node_data.get("id")
                or hashlib.sha1(content.encode("utf-8")).hexdigest()[:12]
            )
            item_id = f"pageindex::{doc_id}::{node_id}"
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            raw_score = node_data.get("score", node_data.get("relevance_score"))
            score = float(raw_score) if isinstance(raw_score, (int, float)) else 1.0 / rank
            results.append(
                {
                    "id": item_id,
                    "content": content,
                    "score": score,
                    "metadata": {
                        "source": source,
                        "title": str(node_data.get("title") or document.get("title") or source),
                        "doc_type": str(document.get("doc_type") or "legal"),
                        "url": document.get("url") if isinstance(document.get("url"), str) else None,
                        "chunk_index": max(rank - 1, 0),
                    },
                    "retrieval_method": "pageindex",
                }
            )

    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]


if __name__ == "__main__":
    upload_documents()
