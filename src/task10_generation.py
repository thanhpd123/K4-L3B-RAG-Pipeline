"""
Task 10 — Generation có citation.

Hướng dẫn:
    1. Retrieve top-k chunks.
    2. Reorder để giảm lost-in-the-middle.
    3. Format context kèm title và source.
    4. Gọi provider được chọn trong .env.
    5. Trả answer, sources và retrieval_source.

Nếu context không đủ hoặc provider lỗi, trả safe refusal; không bịa thông tin.
"""

import os
from typing import Any

from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve


load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "")

_GEMINI_CLIENTS: dict[str, Any] = {}


def _get_gemini_client(api_key: str) -> Any:
    """Trả về client Gemini đã cache theo API key.

    Phải giữ client trong một biến/module-level cache. Nếu tạo
    ``genai.Client(...)`` ngay trong lời gọi thì đối tượng tạm bị thu hồi và
    đóng kết nối HTTP trước khi request được gửi, sinh lỗi
    "Cannot send a request, as the client has been closed".
    """
    client = _GEMINI_CLIENTS.get(api_key)
    if client is None:
        from google import genai

        client = genai.Client(api_key=api_key)
        _GEMINI_CLIENTS[api_key] = client
    return client

SYSTEM_PROMPT = """Trả lời chỉ từ context được cung cấp.
Mỗi khẳng định phải có citation dạng [Source: <ID>] khớp với ID trong
context. Nếu thiếu evidence, hãy từ chối xác minh."""

SAFE_REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context."""
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label."""
    parts = []
    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk.get("metadata") or {}
        item_id = str(chunk.get("id", f"document-{index}"))
        title = str(metadata.get("title") or "Untitled")
        source = str(metadata.get("source") or "Unknown")
        content = str(chunk.get("content") or "").strip()
        if not content:
            continue
        parts.append(
            f"[Document {index} | ID: {item_id} | Title: {title} | "
            f"Source: {source}]\n{content}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình."""
    provider = LLM_PROVIDER.strip().lower()
    model = LLM_MODEL.strip()
    if not model:
        raise ValueError("LLM_MODEL is not configured")

    if provider == "openai":
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        response = OpenAI(api_key=api_key).chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        text = response.choices[0].message.content

    elif provider == "gemini":
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        response = _get_gemini_client(api_key).models.generate_content(
            model=model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=TEMPERATURE,
                top_p=TOP_P,
            ),
        )
        text = response.text

    elif provider == "anthropic":
        from anthropic import Anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured")
        response = Anthropic(api_key=api_key).messages.create(
            model=model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=1024,
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        text = "".join(
            block.text for block in response.content
            if getattr(block, "type", None) == "text"
        )
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")

    if not isinstance(text, str) or not text.strip():
        raise RuntimeError(f"{provider} returned an empty response")
    return text.strip()


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    if top_k <= 0 or not query.strip():
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}

    try:
        chunks = retrieve(query, top_k=top_k)
    except Exception as error:
        print(f"Retrieval unavailable: {error}")
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}

    if not chunks:
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}

    context = format_context(reorder_for_llm(chunks))
    if not context.strip():
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}

    user_message = f"Context:\n{context}\n\nQuestion: {query.strip()}"
    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as error:
        print(f"Generation unavailable: {error}")
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}

    method = chunks[0].get("retrieval_method")
    retrieval_source = "pageindex" if method == "pageindex" else "hybrid"
    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": retrieval_source,
    }


if __name__ == "__main__":
    print(generate_with_citation("test query"))
