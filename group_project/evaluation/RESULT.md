# RAG evaluation results

## Run information

| Field                              | Value                                                               |
| ---------------------------------- | ------------------------------------------------------------------- |
| Evaluation date                    | 2026-09-25 – 2026-09-26                                             |
| Framework and version              | ragas 0.4.3                                                         |
| Evaluator model                    | `gemini-3.5-flash-lite` (qua endpoint OpenAI-compatible của Gemini) |
| Generator model                    | `gemini-3.5-flash-lite`                                             |
| Embedding model                    | `BAAI/bge-m3` (1024 chiều)                                          |
| Corpus version/commit              | `95e49e4` (nhánh `feat/ui-eval`), 8 tài liệu → 429 chunks           |
| Golden dataset size                | 23 câu; A/B chạy trên 17 câu dùng chung được                        |
| `top_k`                            | 5 cho cả hai config                                                 |
| Fallback threshold and calibration | 0.5171 — in-domain min 0.5631, out-of-domain max 0.4710             |

Threshold được hiệu chỉnh bằng 23 câu in-domain và 5 query ngoài domain (nấu ăn, vé máy bay,
bóng đá, cây cảnh, tạm trú). Hai phân bố tách hoàn toàn nên ngưỡng đặt giữa khoảng trống.
Số liệu thô: `threshold_calibration.json`. Giá trị mặc định `0.3` trong pipeline **thấp hơn**
max của out-of-domain (0.4710), nghĩa là với mặc định đó fallback gần như không bao giờ chạy.

## Configurations

- **Config A — dense-only:** `retrieve(..., use_reranking=False)` → chỉ `semantic_search`
  trên ChromaDB (cosine), không BM25, không RRF.
- **Config B — hybrid + RRF:** `semantic_search` + `lexical_search` (BM25) gộp bằng
  `rerank_rrf(k=60)`, RRF chạy đúng một lần.

Hai config dùng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ khác
retrieval strategy. Cột `use_reranking` trong `evaluation_runs.json` ghi lại khác biệt này.

### Giới hạn số câu của lần chạy

Free tier Gemini giới hạn **500 request/ngày/model**. Một lần chạy A/B đầy đủ cần khoảng
500 request, nên phần chấm điểm của Config B bị dừng ở job #68–#91 vì hết quota.

- Config A: đủ **23/23** câu cho cả 4 metric.
- Config B: chỉ **17/23** câu đủ 4 metric.

Vì vậy bảng dưới đây tính lại **cả hai config trên cùng 17 câu** có đủ điểm ở cả A và B.
So sánh này hợp lệ vì cùng câu hỏi, cùng generator, cùng evaluator, cùng `top_k`.

## Overall scores

| Metric            |   Config A |   Config B |   Delta B−A |
| ----------------- | ---------: | ---------: | ----------: |
| Faithfulness      |     0.9804 |     0.9804 |     +0.0000 |
| Answer relevance  |     0.8524 |     0.8247 |     −0.0277 |
| Context recall    |     0.8824 |     0.9118 |     +0.0294 |
| Context precision |     0.7892 |     0.8127 |     +0.0235 |
| **Average**       | **0.8761** | **0.8824** | **+0.0063** |

Điểm của Config A trên đủ 23 câu (tham chiếu, không dùng để so sánh): faithfulness `0.9565`,
answer relevance `0.7897`, context recall `0.7609`, context precision `0.7225`.

## A/B comparison

- **Cấu hình tốt hơn:** Config B (hybrid + RRF) — trung bình 4 metric cao hơn `+0.0063`.
- **Evidence:** Hybrid cải thiện rõ ở khâu retrieval: context recall `+0.0294` và context
  precision `+0.0235`. Đây là hai metric phản ánh trực tiếp việc BM25 bổ sung các chunk chứa
  từ khoá chính xác (mã band điểm, thuật ngữ như "Task Achievement", con số "1.100.000") mà
  dense search bỏ sót. Faithfulness bằng nhau ở mức trần 0.9804.
- **Trade-off:** Answer relevance giảm nhẹ `−0.0277`, tức hybrid đưa thêm ngữ cảnh có ích cho
  recall nhưng làm loãng mức tập trung của câu trả lời. Latency mỗi câu ≈4,4–4,9s trong cả hai
  config nên chi phí retrieval gần như không đổi; chi phí chủ yếu nằm ở generation.

## Worst performers

|    # | Question                                                                                       | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause                                                                                                        |
| ---: | ---------------------------------------------------------------------------------------------- | ------ | -----------: | --------: | -----: | --------: | ------------- | ----------------------------------------------------------------------------------------------------------------- |
|    1 | Những trường hợp nào được xem là ngoại lệ khi hủy hoặc đổi ngày thi IELTS?                     | A      |         0.67 |      0.00 |   0.00 |      0.00 | retrieval     | Danh sách ngoại lệ trải dài qua nhiều đoạn; top-5 chunk không chứa đoạn ngoại lệ nên cả recall và precision đều 0 |
|    2 | Những trường hợp nào được xem là ngoại lệ khi hủy hoặc đổi ngày thi IELTS?                     | B      |         1.00 |      0.00 |   0.00 |      0.00 | retrieval     | Cùng nguyên nhân trên; BM25 không giúp được vì câu hỏi không chứa từ khoá đặc trưng của đoạn ngoại lệ             |
|    3 | Theo tiêu chí Task Achievement, thí sinh cần viết tối thiểu bao nhiêu từ cho Task 1 và Task 2? | B      |         0.67 |      0.00 |   0.50 |      0.00 | retrieval     | Ngữ cảnh đúng có trong chunk nhưng bị pha loãng; chỉ một nửa bằng chứng được truy xuất                            |

## Recommendations

| Priority | Action                                                                                                      | Evidence from failure analysis                                                   | Expected impact                                  | How to verify                                   |
| -------: | ----------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------ | ----------------------------------------------- |
|        1 | Chunk theo cấu trúc mục/danh sách (giữ trọn một danh sách ngoại lệ trong một chunk) thay vì cắt theo độ dài | Câu `legal-10` có recall `0.00` ở cả hai config vì danh sách ngoại lệ bị cắt rời | Tăng context recall cho các câu hỏi dạng liệt kê | Chạy lại A/B, kỳ vọng recall của `legal-10` > 0 |
|        2 | Thêm bước khử trùng lặp/dồn ngữ cảnh trước khi sinh câu trả lời                                             | Answer relevance của B giảm `−0.0277` khi thêm kết quả BM25                      | Tăng answer relevance mà giữ recall              | Chạy lại A/B trên cùng 17 câu                   |
|        3 | Tăng `top_k` cho các câu hỏi nhiều ý (hoặc dùng query decomposition)                                        | `legal-10` và `news-02` đều là câu hỏi nhiều phần                                | Tăng recall với chi phí token cao hơn            | So recall và chi phí token trước/sau            |

## Bonus experiments

| Experiment     | Baseline | Metric delta | Latency/cost delta | Conclusion                                                                                          |
| -------------- | -------- | -----------: | -----------------: | --------------------------------------------------------------------------------------------------- |
| Chưa thực hiện | —        |            — |                  — | Nằm ngoài phạm vi lần chạy này; các hướng khả thi là HyDE, reranker nâng cao và conversation memory |
