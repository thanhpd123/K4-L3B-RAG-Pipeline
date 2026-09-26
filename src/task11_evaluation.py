"""Task 11 — Evaluation harness: golden dataset, 4 metric và so sánh A/B.

Script này không thuộc danh sách interface bắt buộc trong
docs/MODULE_CONTRACTS.md. Nó ghép các public interface của Task 4-10 để đo
chất lượng retrieval + generation, không sửa đổi hành vi của chúng.

Chạy:
    python -m src.task11_evaluation                # full run (mặc định)
    python -m src.task11_evaluation --limit 3      # smoke test nhanh
    python -m src.task11_evaluation --config a     # chỉ dense-only
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import threading
import time
from pathlib import Path
from typing import Any

import httpx

from dotenv import load_dotenv

from .task10_generation import (
    SAFE_REFUSAL,
    SYSTEM_PROMPT,
    call_llm,
    format_context,
    reorder_for_llm,
)
from .task4_chunking_indexing import EMBEDDING_MODEL
from .task5_semantic_search import semantic_search
from .task9_retrieval_pipeline import retrieve

load_dotenv()

ROOT = Path(__file__).parent.parent
EVALUATION_DIR = ROOT / "group_project" / "evaluation"
GOLDEN_DATASET_PATH = EVALUATION_DIR / "golden_dataset.json"
CALIBRATION_PATH = EVALUATION_DIR / "threshold_calibration.json"
RUNS_PATH = EVALUATION_DIR / "evaluation_runs.json"

TOP_K = 5

# Gemini exposes an OpenAI-compatible endpoint, which avoids the known
# instructor/`HARM_CATEGORY_JAILBREAK` issue documented in ragas for the
# native google-genai adapter.
GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# Gemini free tier cho gemini-3.5-flash-lite giới hạn 15 request/phút. Mọi
# request (generation của pipeline lẫn metric của ragas) đi qua một limiter dùng
# chung, mặc định 13 để chừa biên an toàn. Đây là lý do phải throttle thay vì
# chỉ tăng số lần retry: ragas bỏ job ngay khi gặp 429.
GEMINI_MAX_RPM = int(os.getenv("GEMINI_MAX_RPM", "13"))


class _RateLimiter:
    """Giãn đều request theo số request/phút cho phép."""

    def __init__(self, max_per_minute: int) -> None:
        self._interval = 60.0 / max(1, max_per_minute)
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            if now < self._next_allowed:
                time.sleep(self._next_allowed - now)
            self._next_allowed = max(now, self._next_allowed) + self._interval


_LIMITER = _RateLimiter(GEMINI_MAX_RPM)


class _ThrottledTransport(httpx.BaseTransport):
    """httpx transport bọc limiter để mọi request của ragas đều được giãn."""

    def __init__(self, inner: httpx.BaseTransport, limiter: _RateLimiter) -> None:
        self._inner = inner
        self._limiter = limiter

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self._limiter.wait()
        return self._inner.handle_request(request)


OUT_OF_DOMAIN_QUERIES = [
    "Cách nấu phở bò ngon tại nhà",
    "Giá vé máy bay Hà Nội đi Tokyo tháng 12",
    "Lịch thi đấu Ngoại hạng Anh tối nay",
    "Cách trồng cây lưỡi hổ trong nhà",
    "Thủ tục đăng ký tạm trú tạm vắng mới nhất",
]

CONFIGS = {
    "A": {"label": "dense-only", "use_reranking": False},
    "B": {"label": "hybrid + RRF", "use_reranking": True},
}


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
def load_golden_dataset(limit: int | None = None) -> list[dict]:
    """Đọc golden dataset và kiểm tra các field bắt buộc."""
    cases = json.loads(GOLDEN_DATASET_PATH.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise ValueError("golden_dataset.json must contain a list")
    for index, case in enumerate(cases):
        for key in ("question", "expected_answer", "expected_context"):
            value = case.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"golden case {index} has invalid {key}")
    if limit is not None:
        cases = cases[:limit]
    return cases


# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------
def answer_query(query: str, top_k: int = TOP_K, use_reranking: bool = True) -> dict:
    """Chạy retrieval + generation với đúng một cấu hình retrieval.

    Tái sử dụng building block của Task 10 để config A/B chỉ khác nhau ở
    retrieval strategy, mọi thành phần còn lại giữ nguyên.
    """
    empty = {"answer": SAFE_REFUSAL, "contexts": [], "sources": []}
    try:
        chunks = retrieve(query, top_k=top_k, use_reranking=use_reranking)
    except Exception as error:  # PageIndex/provider lỗi không được làm sập eval
        print(f"  retrieval failed: {error}")
        return empty

    if not chunks:
        return empty

    context = format_context(reorder_for_llm(chunks))
    if not context.strip():
        return empty

    user_message = f"Context:\n{context}\n\nQuestion: {query.strip()}"
    try:
        # Generation đi qua google-genai (không dùng transport của ragas) nên
        # phải tự giãn nhịp theo cùng một limiter.
        _LIMITER.wait()
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as error:
        print(f"  generation failed: {error}")
        return empty

    return {
        "answer": answer,
        "contexts": [str(chunk.get("content") or "") for chunk in chunks],
        "sources": chunks,
    }


def collect_records(cases: list[dict], use_reranking: bool) -> list[dict]:
    """Sinh answer + context cho từng câu hỏi trong golden dataset."""
    records = []
    for index, case in enumerate(cases, start=1):
        started = time.perf_counter()
        output = answer_query(case["question"], top_k=TOP_K, use_reranking=use_reranking)
        latency = time.perf_counter() - started
        records.append(
            {
                "id": case["id"],
                "question": case["question"],
                "response": output["answer"],
                "retrieved_contexts": output["contexts"],
                "reference": case["expected_answer"],
                "latency_s": round(latency, 3),
            }
        )
        print(
            f"  [{index}/{len(cases)}] {case['id']}: "
            f"{len(output['contexts'])} contexts, {latency:.1f}s"
        )
    return records


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def _eval_embeddings(model_name: str) -> Any:
    """Embedding cho evaluator với đầy đủ API mà các metric yêu cầu.

    ``ragas.embeddings.HuggingFaceEmbeddings`` (interface mới) chỉ có
    ``embed_text``/``embed_texts``, trong khi ``AnswerRelevancy`` gọi
    ``embed_query``/``embed_documents``. Lớp ``HuggingfaceEmbeddings`` legacy
    thì thiếu implementation async nên không instantiate được. Vì vậy bọc lớp
    mới và bổ sung đúng những method còn thiếu.
    """
    import asyncio

    from ragas.embeddings import HuggingFaceEmbeddings

    class _SentenceTransformerEmbeddings(HuggingFaceEmbeddings):
        def embed_query(self, text: str) -> list[float]:
            return self.embed_text(text)

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return self.embed_texts(texts)

        async def aembed_query(self, text: str) -> list[float]:
            return await asyncio.to_thread(self.embed_query, text)

        async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
            return await asyncio.to_thread(self.embed_documents, texts)

    return _SentenceTransformerEmbeddings(model=model_name)


def build_evaluator():
    """Tạo LLM + embeddings cho ragas, dispatch theo LLM_PROVIDER."""
    from ragas.llms import llm_factory

    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    model = os.getenv("LLM_MODEL", "").strip()
    if not model:
        raise ValueError("LLM_MODEL is not configured")

    if provider in {"gemini", "google"}:
        from openai import OpenAI

        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        http_client = httpx.Client(
            transport=_ThrottledTransport(httpx.HTTPTransport(), _LIMITER),
            timeout=120.0,
        )
        client = OpenAI(
            api_key=api_key,
            base_url=GEMINI_OPENAI_BASE_URL,
            http_client=http_client,
        )
        llm = llm_factory(model, provider="openai", client=client)
    elif provider == "openai":
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        llm = llm_factory(model, provider="openai", client=OpenAI(api_key=api_key))
    elif provider == "anthropic":
        from anthropic import Anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured")
        llm = llm_factory(
            model, provider="anthropic", client=Anthropic(api_key=api_key)
        )
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER for evaluation: {provider}")

    embeddings = _eval_embeddings(EMBEDDING_MODEL)
    return llm, embeddings


def build_metrics(llm: Any, embeddings: Any) -> list[Any]:
    """4 metric theo rubric: faithfulness, answer relevance, recall, precision."""
    from ragas.metrics import (
        AnswerRelevancy,
        Faithfulness,
        LLMContextPrecisionWithReference,
        LLMContextRecall,
    )

    return [
        Faithfulness(llm=llm),
        # strictness=1: endpoint OpenAI-compatible của Gemini trả 1 generation
        # bất kể n=3, nên khai báo thẳng để tránh cảnh báo sai lệch.
        AnswerRelevancy(llm=llm, embeddings=embeddings, strictness=1),
        LLMContextRecall(llm=llm),
        LLMContextPrecisionWithReference(llm=llm),
    ]


def score_records(records: list[dict], llm: Any, embeddings: Any, metrics: list[Any]) -> dict:
    """Chấm 4 metric bằng ragas và trả về điểm trung bình + chi tiết từng câu."""
    from ragas import EvaluationDataset, SingleTurnSample, evaluate
    from ragas.run_config import RunConfig

    samples = [
        SingleTurnSample(
            user_input=record["question"],
            response=record["response"],
            retrieved_contexts=record["retrieved_contexts"],
            reference=record["reference"],
        )
        for record in records
    ]

    result = evaluate(
        dataset=EvaluationDataset(samples=samples),
        metrics=metrics,
        llm=llm,
        embeddings=embeddings,
        experiment_name="rag-eval",
        run_config=RunConfig(max_retries=8, max_wait=90),
        raise_exceptions=False,
        show_progress=False,
        batch_size=1,
    )
    frame = result.to_pandas()

    per_case = []
    for position, record in enumerate(records):
        row = frame.iloc[position]
        per_case.append(
            {
                "id": record["id"],
                "question": record["question"],
                "scores": {
                    metric.name: _clean(row.get(metric.name)) for metric in metrics
                },
                "latency_s": record["latency_s"],
                "contexts_count": len(record["retrieved_contexts"]),
            }
        )

    means = {
        metric.name: _mean(
            [case["scores"][metric.name] for case in per_case]
        )
        for metric in metrics
    }
    return {"means": means, "per_case": per_case}


def _clean(value: Any) -> float | None:
    """Chuẩn hoá giá trị metric: NaN/None -> None, còn lại -> float."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return round(number, 4)


def _mean(values: list[float | None]) -> float | None:
    usable = [value for value in values if value is not None]
    if not usable:
        return None
    return round(statistics.fmean(usable), 4)


# ---------------------------------------------------------------------------
# Threshold calibration
# ---------------------------------------------------------------------------
def calibrate_threshold() -> dict:
    """Đo dense cosine score gốc cho query in-domain và out-of-domain.

    Fallback trong Task 9 so sánh threshold với cosine score gốc của dense
    search, nên hiệu chỉnh phải dùng chính thang đo đó.
    """
    in_domain = load_golden_dataset()
    in_scores: list[dict] = []
    out_scores: list[dict] = []

    for case in in_domain:
        results = semantic_search(case["question"], top_k=TOP_K)
        in_scores.append(
            {
                "query": case["question"],
                "best_cosine": round(float(results[0]["score"]), 4) if results else 0.0,
            }
        )

    for query in OUT_OF_DOMAIN_QUERIES:
        results = semantic_search(query, top_k=TOP_K)
        out_scores.append(
            {
                "query": query,
                "best_cosine": round(float(results[0]["score"]), 4) if results else 0.0,
            }
        )

    in_values = [item["best_cosine"] for item in in_scores]
    out_values = [item["best_cosine"] for item in out_scores]
    suggested = round((min(in_values) + max(out_values)) / 2, 4)

    report = {
        "in_domain": in_scores,
        "out_of_domain": out_scores,
        "summary": {
            "in_domain_min": min(in_values),
            "in_domain_median": round(statistics.median(in_values), 4),
            "in_domain_max": max(in_values),
            "out_of_domain_min": min(out_values),
            "out_of_domain_median": round(statistics.median(out_values), 4),
            "out_of_domain_max": max(out_values),
            "suggested_threshold": suggested,
        },
    }

    print("\nThreshold calibration (dense cosine gốc):")
    print(f"  in-domain  : min={report['summary']['in_domain_min']} "
          f"median={report['summary']['in_domain_median']} "
          f"max={report['summary']['in_domain_max']}")
    print(f"  out-domain : min={report['summary']['out_of_domain_min']} "
          f"median={report['summary']['out_of_domain_median']} "
          f"max={report['summary']['out_of_domain_max']}")
    print(f"  suggested threshold: {suggested}")

    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
    CALIBRATION_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  saved: {CALIBRATION_PATH.relative_to(ROOT)}")
    return report


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def _write_run(run: dict) -> None:
    """Ghi kết quả hiện có ra đĩa để không mất tiến độ giữa chừng."""
    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_PATH.write_text(
        json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG evaluation harness")
    parser.add_argument("--limit", type=int, default=None, help="chỉ chạy N câu đầu")
    parser.add_argument(
        "--config",
        choices=["a", "b", "both"],
        default="both",
        help="cấu hình retrieval cần chạy",
    )
    parser.add_argument(
        "--skip-calibration",
        action="store_true",
        help="bỏ qua bước hiệu chỉnh threshold",
    )
    args = parser.parse_args()

    cases = load_golden_dataset(limit=args.limit)
    print(f"Golden dataset: {len(cases)} câu hỏi")

    if not args.skip_calibration:
        calibrate_threshold()

    llm, embeddings = build_evaluator()
    metrics = build_metrics(llm, embeddings)
    print("Evaluator đã sẵn sàng: " + ", ".join(metric.name for metric in metrics))

    selected = ["A", "B"] if args.config == "both" else [args.config.upper()]
    run: dict[str, Any] = {"top_k": TOP_K, "configs": {}}

    for key in selected:
        config = CONFIGS[key]
        print(f"\n=== Config {key} — {config['label']} ===")
        records = collect_records(cases, use_reranking=config["use_reranking"])
        scored = score_records(records, llm, embeddings, metrics)
        run["configs"][key] = {
            "label": config["label"],
            "use_reranking": config["use_reranking"],
            "means": scored["means"],
            "per_case": scored["per_case"],
        }
        print(f"  means: {scored['means']}")
        # Ghi ngay sau mỗi config: một lần chạy dài có thể đứt vì rate limit
        # hoặc hết thời gian, khi đó kết quả của config đã xong vẫn giữ được.
        _write_run(run)

    if len(run["configs"]) == 2:
        deltas = {}
        for metric_name in run["configs"]["A"]["means"]:
            a_value = run["configs"]["A"]["means"][metric_name]
            b_value = run["configs"]["B"]["means"][metric_name]
            if a_value is None or b_value is None:
                deltas[metric_name] = None
            else:
                deltas[metric_name] = round(b_value - a_value, 4)
        run["delta_b_minus_a"] = deltas
        print(f"\nDelta (B - A): {deltas}")

    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_PATH.write_text(
        json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nSaved: {RUNS_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
