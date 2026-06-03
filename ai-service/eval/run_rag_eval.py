# 展示说明：V0.3 RAG 批量评估工具，执行 120 条 JSONL case 并落盘汇总指标与 case 级定位数据，支持临时报告输出。
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rag.query_engine import RagQueryEngine, load_eval_cases  # noqa: E402


# 安全平均值工具：评估列表为空时返回 0，避免本地演示脚本异常中断。
def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


# 批量评估主流程：逐条调用 /rag/query 同款引擎，聚合召回、忠实度、引用、租户隔离和转人工准确率。
def run_eval(
    dataset_root: Path | None = None,
    report_path: Path | None = None,
    include_case_results: bool = True,
) -> dict[str, Any]:
    engine = RagQueryEngine(dataset_root=dataset_root)
    cases = load_eval_cases(dataset_root=dataset_root)

    context_recall: list[float] = []
    faithfulness: list[float] = []
    citation_coverage: list[float] = []
    hallucination_risk: list[float] = []
    rewrite_accept_rate: list[float] = []
    retrieval_latency: list[float] = []
    handoff_matches = 0
    tenant_leak_count = 0
    expected_doc_hit_rate: list[float] = []
    case_results: list[dict[str, Any]] = []

    for case in cases:
        result = engine.query(
            tenant=case["tenant"],
            query=case["question"],
            top_k=5,
            expected_doc_ids=case["expected_doc_ids"],
            expected_evidence_keywords=case["expected_evidence_keywords"],
        )
        metrics = result["trace"]["metrics"]
        context_recall.append(metrics["context_recall"])
        faithfulness.append(metrics["faithfulness"])
        citation_coverage.append(metrics["citation_coverage"])
        hallucination_risk.append(metrics["hallucination_risk"])
        rewrite_accept_rate.append(metrics["rewrite_accept_rate"])
        retrieval_latency.append(metrics["retrieval_latency_ms"])
        tenant_leak_count += metrics["tenant_leak_count"]
        expected_doc_hit_rate.append(metrics.get("expected_doc_hit_rate", 0.0))
        handoff_matched = bool(result["should_handoff"]) == bool(case["should_handoff"])
        if handoff_matched:
            handoff_matches += 1
        if include_case_results:
            case_results.append(
                {
                    "id": case["id"],
                    "tenant": case["tenant"],
                    "should_handoff": result["should_handoff"],
                    "expected_should_handoff": case["should_handoff"],
                    "handoff_matched": handoff_matched,
                    "fallback_reason": result["fallback_reason"],
                    "citation_doc_ids": [citation["doc_id"] for citation in result["citations"]],
                    "expected_doc_ids": case["expected_doc_ids"],
                    "metrics": metrics,
                }
            )

    summary = {
        "total_cases": len(cases),
        "context_recall": round(average(context_recall), 4),
        "expected_doc_hit_rate": round(average(expected_doc_hit_rate), 4),
        "citation_coverage": round(average(citation_coverage), 4),
        "faithfulness": round(average(faithfulness), 4),
        "hallucination_risk": round(average(hallucination_risk), 4),
        "rewrite_accept_rate": round(average(rewrite_accept_rate), 4),
        "tenant_leak_count": tenant_leak_count,
        "avg_retrieval_latency_ms": round(average(retrieval_latency), 2),
        "handoff_accuracy": round(handoff_matches / len(cases), 4) if cases else 0.0,
    }
    report = {
        "version": "0.3.0",
        "dataset": "contactflow_demo_kb_v0.2",
        "summary": summary,
        "cases": case_results,
    }

    target_report = report_path
    if target_report is None and dataset_root is None:
        target_report = engine.dataset_root / "eval" / "latest_report.json"
    if target_report:
        target_report.parent.mkdir(parents=True, exist_ok=True)
        target_report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return report


# 命令行参数解析：允许把评估报告写到临时路径，避免发布前复验污染已提交的 latest_report.json。
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ContactFlow AI RAG evaluation cases.")
    parser.add_argument("--dataset-root", type=Path, default=None)
    parser.add_argument("--report-output", type=Path, default=None)
    parser.add_argument("--no-case-results", action="store_true")
    return parser.parse_args()


# 命令行入口：打印核心评估指标，并默认更新 latest_report.json。
def main() -> None:
    args = parse_args()
    report = run_eval(
        dataset_root=args.dataset_root,
        report_path=args.report_output,
        include_case_results=not args.no_case_results,
    )
    summary = report["summary"]

    print("ContactFlow AI RAG Eval v0.3")
    print(f"Total Cases: {summary['total_cases']}")
    print(f"Context Recall: {summary['context_recall']:.2f}")
    print(f"Expected Doc Hit Rate: {summary['expected_doc_hit_rate']:.2f}")
    print(f"Citation Coverage: {summary['citation_coverage']:.2f}")
    print(f"Faithfulness: {summary['faithfulness']:.2f}")
    print(f"Hallucination Risk: {summary['hallucination_risk']:.2f}")
    print(f"Rewrite Accept Rate: {summary['rewrite_accept_rate']:.2f}")
    print(f"Tenant Leak Count: {summary['tenant_leak_count']}")
    print(f"Avg Retrieval Latency: {summary['avg_retrieval_latency_ms']:.0f}ms")
    print(f"Handoff Accuracy: {summary['handoff_accuracy']:.2f}")


if __name__ == "__main__":
    main()
