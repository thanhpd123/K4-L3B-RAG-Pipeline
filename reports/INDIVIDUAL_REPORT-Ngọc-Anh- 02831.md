# Báo cáo đóng góp cá nhân

## Thông tin

- Họ và tên: Phạm Thị Ngọc Anh
- Mã học viên: 2A202602831
- Nhóm: A-04
- Repository/branch: `https://github.com/thanhpd123/K4-L3B-RAG-Pipeline` / `ngocanh`

## Phần việc đã thực hiện

| Module/deliverable      | Việc tôi trực tiếp làm                                                                                                                                                                   | File/commit                                                                                              | Trạng thái |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ---------- |
| Thu thập tài liệu IELTS | Bổ sung 3 PDF về chính sách, cấu trúc bài thi và thang chấm IELTS; hoàn thiện hàm kiểm tra số lượng và định dạng tài liệu đầu vào.                                                       | `data/landing/legal/`, `src/task1_collect_legal_docs.py`; commit `b7b7f63`                               | Done       |
| Crawl bài viết          | Chọn 5 URL công khai từ IDP IELTS, triển khai crawl bất đồng bộ bằng Crawl4AI, kiểm tra nội dung rỗng và lưu đủ `url`, `title`, `date_crawled`, `content_markdown`.                      | `src/task2_crawl_news.py`, `data/landing/news/article_01.json`–`article_05.json`; commit `02fefc2`       | Done       |
| Chuẩn hoá corpus        | Chuyển 3 tài liệu pháp lý và 5 bài viết sang Markdown; giữ tiêu đề, URL và thời điểm crawl cho bài viết; bỏ qua đầu ra rỗng và ghi đè theo tên ổn định để tránh file trùng khi chạy lại. | `src/task3_convert_markdown.py`, `data/standardized/legal/`, `data/standardized/news/`; commit `b7b7f63` | Done       |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Chuẩn hoá mỗi bài crawl thành JSON có metadata cố định và dùng thời gian UTC có timezone.
   **Lý do/evidence:** Contract dữ liệu của bài tập yêu cầu đủ bốn trường; kiểm tra `test_corpus_has_required_news_with_metadata` đã pass cho cả 5 file. Việc kiểm tra `content_markdown` rỗng giúp không đưa bài crawl lỗi vào corpus.
   **Trade-off:** Nội dung thô vẫn chứa một phần menu, liên kết và boilerplate của website; cần thêm bước lọc nội dung chính để tăng độ chính xác retrieval.

2. **Quyết định:** Ưu tiên MarkItDown khi chuyển PDF/DOCX, có fallback theo định dạng và không tạo file Markdown rỗng.
   **Lý do/evidence:** Một luồng chuyển đổi dùng được cho nhiều định dạng và tạo đủ 8/8 file chuẩn hoá. Tên đầu ra được suy ra từ tên nguồn nên có thể chạy lại mà không sinh bản sao.
   **Trade-off:** Chất lượng trích xuất phụ thuộc cấu trúc file nguồn; fallback `fitz`/`python-docx` cũng cần dependency tương ứng nếu MarkItDown thất bại.

## Kiểm thử và kết quả

- `python -m src.task1_collect_legal_docs`: tìm thấy và xác thực đủ 3 tài liệu (`IELTS_policies.pdf`, `scoring_barem.pdf`, `test_format.pdf`).
- Ba acceptance test về corpus đều pass: đủ 3 tài liệu pháp lý, đủ 5 JSON có metadata và đủ đầu ra chuẩn hoá cho cả hai loại nguồn (`3 passed`).
- `python -m py_compile src/task1_collect_legal_docs.py src/task2_crawl_news.py src/task3_convert_markdown.py`: pass.
- Kết quả đầu ra: 8 file nguồn trong landing và 8 file Markdown chuẩn hoá, tổng khoảng 23.194 từ.
- Trước khi thực hiện, các hàm crawl và chuyển đổi còn là khung `NotImplementedError`; sau khi hoàn thiện, corpus đã đáp ứng ba kiểm tra acceptance tương ứng.

## Điều còn hạn chế

- Corpus bài viết còn lẫn navigation/boilerplate của trang IDP; phần legal chưa gắn URL nguồn trực tiếp vào đầu file Markdown.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện là trích riêng nội dung bài viết chính và bổ sung kiểm tra chất lượng nội dung sau crawl, sau đó mới index lại corpus.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 25/09/2026
- Tên thành viên: Phạm Thị Ngọc Anh
