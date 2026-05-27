from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rag.query_engine import RagQueryEngine, load_eval_cases  # noqa: E402


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def main() -> None:
    engine = RagQueryEngine()
    cases = load_eval_cases()

    context_recall: list[float] = []
    faithfulness: list[float] = []
    citation_coverage: list[float] = []
    hallucination_risk: list[float] = []
    rewrite_accept_rate: list[float] = []
    retrieval_latency: list[float] = []
    handoff_matches = 0
    tenant_leak_count = 0
    expected_doc_hit_rate: list[float] = []

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
        if bool(result["should_handoff"]) == bool(case["should_handoff"]):
            handoff_matches += 1

    print("ContactFlow AI RAG Eval v0.2")
    print(f"Total Cases: {len(cases)}")
    print(f"Context Recall: {average(context_recall):.2f}")
    print(f"Expected Doc Hit Rate: {average(expected_doc_hit_rate):.2f}")
    print(f"Citation Coverage: {average(citation_coverage):.2f}")
    print(f"Faithfulness: {average(faithfulness):.2f}")
    print(f"Hallucination Risk: {average(hallucination_risk):.2f}")
    print(f"Rewrite Accept Rate: {average(rewrite_accept_rate):.2f}")
    print(f"Tenant Leak Count: {tenant_leak_count}")
    print(f"Avg Retrieval Latency: {average(retrieval_latency):.0f}ms")
    print(f"Handoff Accuracy: {handoff_matches / len(cases):.2f}")


if __name__ == "__main__":
    main()
