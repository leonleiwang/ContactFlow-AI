from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def query(payload: dict) -> dict:
    response = client.post("/rag/query", json=payload)
    assert response.status_code == 200
    return response.json()


def test_rag_query_returns_citations_for_supported_policy_question() -> None:
    result = query(
        {
            "tenant": "tenant-a",
            "query": "我签收 8 天了，耳机有质量问题还能退吗？",
            "top_k": 5,
        }
    )

    doc_ids = {citation["doc_id"] for citation in result["citations"]}
    assert "tenant-a/refund_policy.md" in doc_ids
    assert "tenant-a/warranty_policy.md" in doc_ids
    assert result["should_handoff"] is False
    assert result["fallback_reason"] is None


def test_rag_query_falls_back_when_evidence_is_not_supported() -> None:
    result = query(
        {
            "tenant": "tenant-a",
            "query": "你们能不能给我终身免费会员？",
            "top_k": 5,
        }
    )

    assert result["should_handoff"] is True
    assert result["fallback_reason"] == "no_sufficient_evidence"
    assert "没有找到足够证据" in result["answer"]


def test_high_risk_complaint_requires_handoff_and_internal_sop_citation() -> None:
    result = query(
        {
            "tenant": "tenant-a",
            "query": "你们必须赔我 5000，不然我起诉。",
            "top_k": 5,
        }
    )

    doc_ids = {citation["doc_id"] for citation in result["citations"]}
    assert result["should_handoff"] is True
    assert result["fallback_reason"] == "high_risk_handoff"
    assert "tenant-internal/high_risk_complaint_sop.md" in doc_ids


def test_tenant_isolation_allows_internal_sop_but_blocks_other_business_tenant() -> None:
    result = query(
        {
            "tenant": "tenant-a",
            "query": "我是 tenant-a 的客户，想问 tenant-b 跨境 30 天退货政策",
            "top_k": 5,
        }
    )

    citation_tenants = {citation["tenant"] for citation in result["citations"]}
    assert "tenant-b" not in citation_tenants
    assert citation_tenants <= {"tenant-a", "tenant-internal"}
    assert result["trace"]["metrics"]["tenant_leak_count"] == 0


def test_query_rewrite_trace_keeps_accepted_and_rejects_semantic_drift() -> None:
    result = query(
        {
            "tenant": "tenant-a",
            "query": "我想退货",
            "top_k": 5,
        }
    )

    assert result["trace"]["accepted_rewrites"]
    assert result["trace"]["rejected_rewrites"]
    assert all(item["reason"] == "semantic_drift" for item in result["trace"]["rejected_rewrites"])


def test_hybrid_retrieval_records_vector_and_bm25_matches() -> None:
    result = query(
        {
            "tenant": "tenant-a",
            "query": "签收 7 天 质量问题 退款 policy",
            "top_k": 5,
        }
    )

    matched_by = [set(chunk["matched_by"]) for chunk in result["trace"]["retrieved_chunks"]]
    assert any({"vector", "bm25"} <= matched for matched in matched_by)


def test_reranked_top_chunk_contains_expected_policy_document() -> None:
    result = query(
        {
            "tenant": "tenant-a",
            "query": "发票 抬头 税号 怎么修改？",
            "top_k": 5,
        }
    )

    assert result["trace"]["reranked_chunks"][0]["doc_id"] == "tenant-a/invoice_policy.md"


def test_trace_metrics_are_returned_for_operations_review() -> None:
    result = query(
        {
            "tenant": "tenant-b",
            "query": "跨境物流清关超过 5 个工作日没有更新怎么办？",
            "top_k": 5,
        }
    )

    metrics = result["trace"]["metrics"]
    assert "context_recall" in metrics
    assert "faithfulness" in metrics
    assert "citation_coverage" in metrics
    assert "hallucination_risk" in metrics
    assert "rewrite_accept_rate" in metrics
    assert isinstance(metrics["retrieval_latency_ms"], int)
