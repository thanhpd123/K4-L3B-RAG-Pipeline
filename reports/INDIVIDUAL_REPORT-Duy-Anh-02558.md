# Báo cáo đóng góp cá nhân

## Thông tin

- Họ và tên: Trần Hoàng Duy Anh
- Mã học viên: 2A202602558
- Nhóm: A-04
- Repository/branch: `https://github.com/thanhpd123/K4-L3B-RAG-Pipeline` / `duyanh`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit | Trạng thái |
| ------------------ | ---------------------- | ----------- | ---------- |
| Generation có citation | Sửa lỗi Gemini client bị đóng trước khi request được gửi, giúp chatbot tiếp tục sinh câu trả lời có citation. | `src/task10_generation.py` (`_get_gemini_client`); commit `54a66db` | Done |
| Tài liệu và vệ sinh repository | Bổ sung bước evaluation vào hướng dẫn chạy, loại index/cache khỏi repository và khai báo dependency `httpx`. | `README.md`, `.gitignore`, `pyproject.toml`; commit `54a66db` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Cache Gemini client ở cấp module theo API key thay vì tạo một client tạm trong mỗi lần gọi generation.
   **Lý do/evidence:** Client được tạo trực tiếp trong lời gọi có thể bị thu hồi và đóng HTTP client trước khi request gửi đi, gây lỗi `Cannot send a request, as the client has been closed`. Hàm `_get_gemini_client` giữ client trong `_GEMINI_CLIENTS` và tái sử dụng client cho các request sau.
   **Trade-off:** Client được giữ trong bộ nhớ trong suốt vòng đời process; khi API key thay đổi, cache sẽ giữ một client riêng cho từng key.

2. **Quyết định:** Cập nhật README cùng các file cấu hình repository để quy trình chạy và dependency phản ánh đúng sản phẩm hiện tại.
   **Lý do/evidence:** README có bước chạy evaluation bằng `python -m src.task11_evaluation`; `.gitignore` giúp tránh đưa index/cache vào git; `pyproject.toml` khai báo `httpx` để môi trường cài đặt đủ dependency cần thiết.
   **Trade-off:** Người dùng vẫn cần cấu hình API key trong `.env` và cài dependencies trước khi chạy các bước generation/evaluation.

## Kiểm thử và kết quả

- `pytest -q` → **20 passed** theo kết quả kiểm thử chung của repository.
- Kiểm tra generation với Gemini đã xử lý được lỗi `Cannot send a request, as the client has been closed` bằng cách tái sử dụng client đã cache.
- README cung cấp đầy đủ luồng chính: thu thập, chuẩn hóa, index, chạy chatbot và evaluation.
- Kết quả đầu ra của phần generation giữ đúng contract: câu trả lời, danh sách nguồn và `retrieval_source`; khi provider lỗi hoặc thiếu evidence, pipeline trả về safe refusal.

## Điều còn hạn chế

- Việc kiểm thử trực tiếp với Gemini phụ thuộc API key, quota và trạng thái dịch vụ; kết quả `pytest` không thay thế hoàn toàn kiểm thử end-to-end với provider thật.
- Commit tham chiếu trong lịch sử repository là commit tổng hợp `54a66db`, nên không tách riêng được commit chỉ chứa hai hạng mục trên.
- Nếu có thêm thời gian, tôi sẽ bổ sung một integration test dùng mock Gemini client để kiểm tra rõ vòng đời client và trường hợp client được tái sử dụng giữa nhiều request.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 25/09/2026
- Tên thành viên: Trần Hoàng Duy Anh
