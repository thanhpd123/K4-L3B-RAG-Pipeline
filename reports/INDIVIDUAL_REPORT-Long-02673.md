# Báo cáo đóng góp cá nhân

## Thông tin

- **Họ và tên:** Long (GitHub: `long2110d`)
- **Mã học viên:** Chưa có thông tin trong repository
- **Nhóm:** A-04
- **Repository/branch:** `thanhpd123/K4-L3B-RAG-Pipeline` / `origin/main`
- **Commit đối chiếu:** `95e49e49f85a26bebdb5179524fd8a7f483d7663` — *commit task 7 8 9 app*

## Phần việc đã thực hiện

| Module/deliverable              | Việc tôi trực tiếp làm                                                                                                                                                                                                                       | File/commit                                           | Trạng thái |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- | ---------- |
| Task 7 — Reciprocal Rank Fusion | Cài đặt RRF theo công thức `sum(1 / (k + rank))`; gộp kết quả dense và BM25 theo `id`; loại phiếu trùng trong cùng một danh sách; giữ thứ tự ổn định khi bằng điểm; trả đúng schema với `retrieval_method="hybrid"`.                         | `src/task7_reranking.py`, commit `95e49e4`            | Done       |
| Task 8 — PageIndex fallback     | Tích hợp PageIndex; đọc API key từ biến môi trường; chuyển Markdown sang PDF khi cần; tái sử dụng PDF gốc; cache `doc_id` theo SHA-256; polling có timeout; chuẩn hóa nhiều dạng node trả về; loại kết quả trùng và trả đúng `SearchResult`. | `src/task8_pageindex_vectorless.py`, commit `95e49e4` | Done       |
| Task 9 — Retrieval pipeline     | Ghép semantic search, BM25 và RRF; lấy `2 * top_k` ứng viên; chỉ fuse một lần; dùng cosine score gốc của dense search để quyết định fallback; khi PageIndex lỗi hoặc không có kết quả thì trả hybrid results thay vì làm pipeline crash.     | `src/task9_retrieval_pipeline.py`, commit `95e49e4`   | Done       |

## Quyết định kỹ thuật quan trọng

1. **Dùng RRF dựa trên thứ hạng thay vì cộng trực tiếp cosine score và BM25 score.**

   **Lý do/evidence:** Hai retriever sử dụng thang điểm khác nhau; RRF cho phép kết hợp nhất quán và ưu tiên tài liệu xuất hiện cao ở cả hai danh sách. Test `test_rrf_uses_rank_deduplicates_and_marks_hybrid` kiểm tra tài liệu chung đứng đầu và điểm bằng `1/62 + 1/61`.

   **Trade-off:** RRF không tận dụng trực tiếp độ lớn score và tham số `k=60` chưa được hiệu chỉnh trên golden dataset.

2. **Quyết định fallback bằng dense cosine score và cô lập lỗi PageIndex.**

   **Lý do/evidence:** RRF score chỉ phản ánh thứ hạng nên không phù hợp để so với confidence threshold. Pipeline chỉ gọi PageIndex khi best dense score thấp; mọi lỗi provider được chặn để vẫn trả kết quả hybrid. Các test `test_retrieve_uses_dense_score_for_fallback`, `test_retrieve_fuses_once_when_dense_is_confident` và `test_retrieve_survives_fallback_provider_error` đối chiếu ba nhánh này.

   **Trade-off:** Threshold mặc định `0.3` phụ thuộc embedding model/corpus; fallback qua dịch vụ ngoài làm tăng latency và cần API key.

## Kiểm thử và kết quả

- **Test/query đã dùng:** các contract test cho RRF và retrieval pipeline trong `tests/test_contracts.py`; trường hợp dense score thấp, dense score đủ tin cậy, PageIndex trả kết quả và PageIndex phát sinh lỗi.
- **Kết quả đối chiếu trong code:** RRF loại ID trùng, sắp xếp giảm dần và gắn method `hybrid`; pipeline chỉ fuse một lần, chọn PageIndex khi dense score dưới threshold, đồng thời phục hồi về hybrid khi provider lỗi.
- **Lỗi đã phát hiện và cách xử lý:** Markdown có thể không được PageIndex hỗ trợ trực tiếp nên được chuyển sang PDF; upload trùng được tránh bằng cache SHA-256; response thiếu ID hoặc retrieval lỗi/timeout được phát hiện rõ ràng; exception từ PageIndex không truyền lên UI.
- **Khả năng chạy lại:** `pytest tests/test_contracts.py -q`. Tại máy hiện tại chưa chạy lại được vì `.venv` đang trỏ tới Python 3.11 không còn tồn tại; cần tạo lại virtual environment trước khi nghiệm thu.

## Điều còn hạn chế

- Chưa có bằng chứng smoke test trực tiếp với PageIndex trong môi trường hiện tại; truy vấn lần lượt từng tài liệu có thể chậm khi corpus lớn.
- Nếu có thêm thời gian, tôi sẽ tạo lại môi trường Python, bổ sung mock test riêng cho upload/cache/timeout/response parsing, chạy live smoke test và hiệu chỉnh `SCORE_THRESHOLD` bằng các câu hỏi in-domain/out-of-domain trong golden dataset.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- **Ngày:** 25/09/2026
- **Tên thành viên:** Long (`long2110d`)
