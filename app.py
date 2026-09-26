import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import LLM_MODEL, LLM_PROVIDER, generate_with_citation


load_dotenv()

st.set_page_config(
    page_title="IELTS RAG Assistant",
    page_icon="🎓",
    layout="wide",
)


def render_sources(sources: list[dict], retrieval_source: str) -> None:
    """Hiển thị các đoạn tài liệu được dùng cho câu trả lời."""
    if not sources:
        st.caption("Không có nguồn tham chiếu.")
        return

    st.caption(
        f"Nguồn truy xuất: {retrieval_source} • "
        f"{len(sources)} đoạn tài liệu"
    )
    for index, source in enumerate(sources, start=1):
        metadata = source.get("metadata") or {}
        title = metadata.get("title") or metadata.get("source") or "Không có tiêu đề"
        source_name = metadata.get("source") or "Không rõ nguồn"
        method = source.get("retrieval_method", "unknown")
        score = source.get("score", 0.0)
        item_id = source.get("id", "unknown")

        with st.expander(f"[{index}] {title}"):
            st.markdown(f"**Citation:** `[Source: {item_id}]`")
            st.markdown(f"**File:** `{source_name}`")
            st.markdown(
                f"**Phương pháp:** `{method}` · "
                f"**Score:** `{float(score):.4f}`"
            )

            url = metadata.get("url")
            if isinstance(url, str) and url.startswith(("http://", "https://")):
                st.markdown(f"**URL:** [{url}]({url})")

            content = str(source.get("content") or "").strip()
            if content:
                st.markdown("**Nội dung truy xuất:**")
                st.text(content)


if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("🎓 IELTS RAG")
    st.caption(
        "Hỏi đáp dựa trên tài liệu chính sách, thể lệ thi và "
        "bài viết IELTS trong kho dữ liệu."
    )
    top_k = st.slider("Số đoạn tài liệu", 3, 10, 5)
    st.divider()
    st.caption(f"LLM provider: `{LLM_PROVIDER}`")
    st.caption(f"Model: `{LLM_MODEL or 'chưa cấu hình'}`")

    if st.button("Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("Trợ lý thông tin IELTS")
st.caption(
    "Câu trả lời chỉ dựa trên các nguồn được truy xuất. "
    "Mở phần nguồn bên dưới mỗi câu trả lời để kiểm chứng."
)

if not st.session_state.messages:
    st.info(
        "Ví dụ: Chính sách đổi lịch thi IELTS là gì? "
        "Hoặc: Tiêu chí Task Achievement trong Writing Task 1?"
    )

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_sources(
                message.get("sources", []),
                message.get("retrieval_source", "none"),
            )

query = st.chat_input("Nhập câu hỏi về IELTS...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm kiếm tài liệu và tạo câu trả lời..."):
            try:
                result = generate_with_citation(query, top_k=top_k)
            except Exception as error:
                result = {
                    "answer": (
                        "Tôi không thể xác minh thông tin này từ "
                        "nguồn hiện có."
                    ),
                    "sources": [],
                    "retrieval_source": "none",
                }
                st.error(f"Pipeline gặp lỗi: {error}")

        answer = result["answer"]
        sources = result.get("sources", [])
        retrieval_source = result.get("retrieval_source", "none")
        st.markdown(answer)
        render_sources(sources, retrieval_source)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "retrieval_source": retrieval_source,
        }
    )
