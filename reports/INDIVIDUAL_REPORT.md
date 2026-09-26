# Individual Contribution Report — Phase 2: Index & Search

Giới hạn khuyến nghị: 1 trang, ghi nhận ownership và bằng chứng đóng góp trong sản phẩm RAG Pipeline nhóm.

---

## Thông tin

- **Họ và tên**: Phạm Thanh Sơn
- **Mã học viên**: 2A202602794
- **Nhóm**: Nhóm L3B - RAG Pipeline
- **Repository/branch**: `https://github.com/thanhpd123/K4-L3B-RAG-Pipeline` (branch: `feat/index-search`)

---

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| **Task 4: Chunking & Indexing** | Thiết lập quy trình load 8 tài liệu `.md` từ `data/standardized/`, sinh 429 chunks bằng `RecursiveCharacterTextSplitter` (`CHUNK_SIZE=500`, `CHUNK_OVERLAP=50`). Tích hợp embedding model `BAAI/bge-m3` (1024-dim), phẳng hóa metadata và thực hiện `upsert` vào ChromaDB (`cosine` distance). | `src/task4_chunking_indexing.py` | Done |
| **Task 5: Semantic Search** | Xây dựng hàm `semantic_search(query, top_k)` tái sử dụng `embed_texts()` của Task 4. Chuyển đổi cosine distance thành similarity score (`1 - distance`), khử trùng ID, sắp xếp giảm dần và trả về đúng schema `SearchResult` (`retrieval_method="dense"`). | `src/task5_semantic_search.py` | Done |
| **Task 6: Lexical Search (BM25)** | Xây dựng tokenizer NFC hỗ trợ tiếng Việt và thuật ngữ/con số (vd: `"6.5"`, `"Task 1"`). Sử dụng `BM25Plus` trên cùng tập corpus chunks, hỗ trợ auto-rebuild khi `CORPUS` thay đổi, trả về kết quả theo schema `SearchResult` (`retrieval_method="bm25"`). | `src/task6_lexical_search.py` | Done |
| **Quality Assurance & Verification** | Đảm bảo tuân thủ strict contract. Vượt qua 100% các unit test liên quan trong `tests/test_contracts.py` và linter `ruff check src/`. | `tests/test_contracts.py` | Done |

---

## Quyết định kỹ thuật quan trọng

1. **Quyết định: Sử dụng `BM25Plus` và cơ chế fallback kiểm tra token matching thực tế cho Lexical Search**  
   - **Lý do/evidence**: Với các tập corpus nhỏ (ví dụ trong unit test mocks), thuật toán `BM25Okapi` tiêu chuẩn có thể tính IDF <= 0 cho các từ xuất hiện ở hầu hết văn bản, khiến score bị âm/bằng 0 và bị lọc nhầm. `BM25Plus` bổ sung hằng số delta giúp điểm số luôn thực dương khi có token trùng lặp.  
   - **Trade-off**: Tăng thêm một lượng nhỏ tính toán khi khởi tạo index nhưng đảm bảo độ tin cậy tuyệt đối và không bỏ sót các văn bản liên quan.

2. **Quyết định: Thiết lập ID ổn định (deterministic) và cơ chế `upsert` trên ChromaDB**  
   - **Lý do/evidence**: ID chunk được đặt theo định dạng chuẩn `{doc_id}::chunk_{chunk_index}` suy ra từ đường dẫn tương đối của file nguồn thay vì dùng `uuid` ngẫu nhiên. Khi chạy lại pipeline (re-indexing), số lượng record trong ChromaDB giữ nguyên không đổi (429 records).  
   - **Trade-off**: Cần đảm bảo đường dẫn tài liệu nguồn không bị thay đổi đột ngột giữa các lần index.

---

## Kiểm thử và kết quả

- **Test và Command đã sử dụng**:
  - `python -m src.task4_chunking_indexing` (Kết quả: Loaded 8 documents, 429 chunks, 429 ChromaDB records).
  - `python -m src.task4_chunking_indexing` (Chạy lần 2: Record count giữ nguyên 429, khẳng định tính idempotency).
  - `pytest tests/test_contracts.py -q -k "semantic or lexical or chunk or document or signature or search_result"` (PASSED 7/7 tests).
  - `python -m src.task5_semantic_search` & `python -m src.task6_lexical_search` (Thử nghiệm 3 câu query mẫu: Tiếng Việt, Tiếng Anh và Thuật ngữ "Task Achievement").
  - `python -m ruff check src/` (All checks passed!).

- **Lỗi đã phát hiện và cách xử lý**:
  - *Lỗi 1*: `FakeCollection` trong test không có method `count()`. -> *Xử lý*: Loại bỏ `collection.count()` trong `semantic_search()`, chỉ gọi duy nhất `collection.query()`.
  - *Lỗi 2*: Test monkeypatch biến `CORPUS` làm `lexical_search()` trả kết quả rỗng do dùng cache tĩnh cũ. -> *Xử lý*: Kiểm tra tham chiếu `id(CORPUS)` để tự động phát hiện thay đổi và rebuild BM25 index linh hoạt.

---

## Điều còn hạn chế

- **Hạn chế cụ thể**: Tốc độ khởi tạo model `BAAI/bge-m3` lần đầu tiên cần tải weights (~1.5GB) và tiêu tốn CPU/GPU memory.
- **Thay đổi ưu tiên nếu có thêm thời gian**: Tích hợp thêm băm MD5/SHA256 cho nội dung file nguồn để chỉ re-embed và re-index những file thực sự có sửa đổi nội dung.

---

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- **Ngày**: 26/09/2026
- **Tên thành viên**: Phạm Thanh Sơn
