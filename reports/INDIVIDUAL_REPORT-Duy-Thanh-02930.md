# Individual contribution report

Mỗi thành viên copy template này thành:

```text
reports/<student-id>-<short-name>.md
```

Giới hạn khuyến nghị: 1 trang, không chép lại README hoặc mô tả lý thuyết chung. Báo cáo không phải một bài pipeline cá nhân; mục đích là ghi nhận ownership và bằng chứng đóng góp trong sản phẩm nhóm.

---

## Thông tin

- Họ và tên: Phan Duy Thành
- Mã học viên: 2A202602930
- Nhóm: A-04 
- Repository/branch: `https://github.com/thanhpd123/K4-L3B-RAG-Pipeline` / `feat/ui-eval`

## Phần việc đã thực hiện

| Module/deliverable       | Việc tôi trực tiếp làm                                                             | File/commit/PR                                                                                                      | Trạng thái |
| ------------------------ | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ---------- |
| RRF, fallback, retrieval | Hoàn thiện rerank RRF, PageIndex fallback và retrieval pipeline (RRF chạy một lần) | `src/task7_reranking.py`, `src/task8_pageindex_vectorless.py`, `src/task9_retrieval_pipeline.py` — commit `95e49e4` | Done       |
| Chatbot UI               | Giao diện Streamlit: hiển thị answer, nguồn, retrieval method, score và citation   | `app.py` — commit `95e49e4`                                                                                         | Done       |
| Generation có citation   | Sửa lỗi Gemini client bị đóng khiến chatbot không sinh được câu trả lời            | `src/task10_generation.py` (`_get_gemini_client`)                                                                   | Done       |
| Golden dataset           | Tạo 23 câu Q&A bám corpus thật, có `expected_answer` và `expected_context`         | `group_project/evaluation/golden_dataset.json`                                                                      | Done       |
| Evaluation harness       | Viết module chấm 4 metric, so sánh A/B và hiệu chỉnh threshold                     | `src/task11_evaluation.py`                                                                                          | Done       |
| Hiệu chỉnh threshold     | Đo dense cosine cho query in-domain và out-of-domain, đề xuất ngưỡng 0.5171        | `group_project/evaluation/threshold_calibration.json`                                                               | Done       |
| Tài liệu & vệ sinh repo  | Thêm bước evaluation vào README, ignore index/cache, khai báo `httpx`              | `README.md`, `.gitignore`, `pyproject.toml`                                                                         | Done       |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Fallback so ngưỡng với cosine score gốc của dense search và hiệu chỉnh ngưỡng bằng query in-domain/out-of-domain thay vì dùng mặc định `0.3`.
   **Lý do/evidence:** `threshold_calibration.json` cho in-domain min `0.5631` và out-of-domain max `0.4710` — hai phân bố tách hoàn toàn, nên ngưỡng `0.5171` nằm giữa khoảng trống. Với mặc định `0.3`, mọi query out-of-domain (0.34–0.47) vẫn vượt ngưỡng nên fallback không bao giờ được gọi.
   **Trade-off:** Ngưỡng cao hơn làm PageIndex ít được gọi hơn, đổi lại giảm nguy cơ trả lời bằng context không liên quan; khi corpus thay đổi phải calibrate lại.

2. **Quyết định:** Hai config A/B chỉ khác retrieval strategy (dense-only vs hybrid + RRF), giữ nguyên generator, evaluator, prompt và `top_k`; đồng thời giãn nhịp request ở tầng HTTP transport.
   **Lý do/evidence:** `evaluation_runs.json` ghi `use_reranking` false/true cho A/B nên so sánh quy được về đúng một biến. Free tier Gemini giới hạn 15 request/phút và ragas bỏ job ngay khi gặp 429 (`Max retries exceeded. Total attempts: 1`) — ở lần chạy thử 2 câu, nhiều metric trả `None` vì lỗi này. Sau khi throttle, không còn 429 theo phút.
   **Trade-off:** Throttle làm thời gian chạy tăng lên khoảng 40 phút cho 23 câu × 2 config. Tuy nhiên tổng nhu cầu (~500 request) đúng bằng hạn mức **theo ngày** của free tier nên Config B chỉ hoàn tất 17/23 câu; vì vậy bảng A/B phải tính lại trên 17 câu dùng chung thay vì toàn bộ dataset.

## Kiểm thử và kết quả

- **Test:** `pytest -q` → **20 passed**. Trước khi tạo lại `group_project/evaluation/RESULT.md` thì có `1 failed` là `test_evaluation_report_is_completed`, do commit `a23df34` đã xoá file đó trong khi test vẫn trỏ tới đường dẫn cũ. `test_golden_dataset_has_15_grounded_cases` pass với 23 câu.
- **Query in-domain vs out-of-domain:** 23 câu golden dataset (in-domain) vs 5 query ngoài domain (nấu ăn, vé máy bay, bóng đá, cây cảnh, tạm trú). Kết quả: in-domain min `0.5631`, out-domain max `0.4710` — không chồng lấn.
- **Kết quả A/B** (ragas 0.4.3, evaluator `gemini-3.5-flash-lite`, embedding `BAAI/bge-m3`, `top_k=5`). Free tier Gemini giới hạn 500 request/ngày/model nên Config B chỉ chấm được 17/23 câu; cả hai config được tính lại trên **cùng 17 câu dùng chung**:

  | Metric            | A — dense-only | B — hybrid + RRF |   Delta B−A |
  | ----------------- | -------------: | ---------------: | ----------: |
  | Faithfulness      |         0.9804 |           0.9804 |     +0.0000 |
  | Answer relevancy  |         0.8524 |           0.8247 |     −0.0277 |
  | Context recall    |         0.8824 |           0.9118 |     +0.0294 |
  | Context precision |         0.7892 |           0.8127 |     +0.0235 |
  | **Average**       |     **0.8761** |       **0.8824** | **+0.0063** |

  Config A trên đủ 23 câu: faithfulness `0.9565`, answer relevancy `0.7897`, context recall `0.7609`, context precision `0.7225`.

- **Lỗi đã phát hiện và cách xử lý:**
  1. `Cannot send a request, as the client has been closed` — `genai.Client(api_key=...)` tạo tạm bị thu hồi và đóng HTTP client trước khi gửi request. Cô lập bằng 4 biến thể (client tạo tạm vs client gán biến); sửa bằng cache client trong `_get_gemini_client`. Đây là bug có sẵn nên trước đó `app.py` không sinh được câu trả lời với provider Gemini.
  2. `AttributeError: 'HuggingFaceEmbeddings' object has no attribute 'embed_query'` — lớp embeddings interface mới của ragas thiếu `embed_query`/`embed_documents` mà `AnswerRelevancy` gọi, còn lớp legacy thì thiếu implementation async nên không instantiate được. Sửa bằng adapter bọc lớp mới và bổ sung đúng hai method thiếu.
  3. `429 RESOURCE_EXHAUSTED` — free tier chỉ 15 request/phút và ragas không retry hiệu quả. Sửa bằng rate limiter dùng chung, gắn vào `httpx` transport của client evaluator và giãn cả call generation của pipeline.

## Điều còn hạn chế

- **Hạn chế:** Free tier Gemini chỉ cho 500 request/ngày/model, đúng bằng chi phí một lần chạy A/B đầy đủ, nên Config B chỉ chấm được 17/23 câu và bảng A/B phải tính lại trên 17 câu dùng chung thay vì toàn bộ golden dataset. Ngoài ra PageIndex fallback chưa được kiểm chứng end-to-end vì `.env` không có `PAGEINDEX_API_KEY`; nhánh này mới chỉ được xác nhận qua unit test dùng monkeypatch.
- **Nếu có thêm thời gian:** Chạy lại Config B cho đủ 23 câu sau khi quota reset (`python -m src.task11_evaluation --config b`), lặp 3 lần lấy trung bình để giảm nhiễu do LLM, và bổ sung retry/backoff cho nhánh OpenAI/Anthropic trong `call_llm` (hiện chỉ nhánh Gemini đã được xác minh).

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 25/09/2026
- Tên thành viên: Phan Duy Thành
