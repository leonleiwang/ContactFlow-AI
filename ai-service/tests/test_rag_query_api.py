# 展示说明：RAG Query API 测试覆盖证据召回、fallback、租户隔离、trace 指标和 V0.3 接口入参质量约束。
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# RAG 查询测试工具：统一断言 200 响应和 UTF-8 JSON Content-Type。
def query(payload: dict) -> dict:
    response = client.post("/rag/query", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json; charset=utf-8")
    return response.json()


# 有证据问题：应返回 tenant-a 退款和保修相关引用，不触发转人工。
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


# 无证据权益诉求：不得编造终身免费会员，应进入 no_sufficient_evidence fallback。
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


# 高风险投诉：涉及赔偿、起诉等场景必须转人工，并引用内部高风险 SOP。
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


# 租户隔离：业务租户不能召回其他业务租户文档，但允许引用内部 SOP。
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


# Query Rewrite trace：保留通过语义校验的 rewrite，并暴露被 semantic drift 拒绝的候选。
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


# 混合召回：trace 中应能看到 vector 与 BM25 两路命中，便于评估检索链路。
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


# 重排序结果：发票问题的最高排序 chunk 应落在发票政策文档上。
def test_reranked_top_chunk_contains_expected_policy_document() -> None:
    result = query(
        {
            "tenant": "tenant-a",
            "query": "发票 抬头 税号 怎么修改？",
            "top_k": 5,
        }
    )

    assert result["trace"]["reranked_chunks"][0]["doc_id"] == "tenant-a/invoice_policy.md"


# 运营指标：API 返回 context recall、faithfulness、hallucination risk 等可观测字段。
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
    assert result["trace"]["rerank_mode"] in {"lightweight", "model", "empty"}
    assert "rerank_degraded_reason" in result["trace"]


# 接口边界：top_k 必须在 1-10 内，避免低质量调用拖垮检索链路或绕过约定。
def test_rag_query_rejects_invalid_top_k() -> None:
    response = client.post(
        "/rag/query",
        json={"tenant": "tenant-a", "query": "物流超过承诺时间怎么办？", "top_k": 50},
    )

    assert response.status_code == 422


# 接口边界：禁止未定义字段进入 API，避免前端或调用方误以为额外参数已生效。
def test_rag_query_rejects_unknown_fields() -> None:
    response = client.post(
        "/rag/query",
        json={"tenant": "tenant-a", "query": "物流超过承诺时间怎么办？", "top_k": 5, "debug": True},
    )

    assert response.status_code == 422


# 接口边界：Assist API 只接受明确优先级，非法枚举值由 Pydantic 拒绝。
def test_assist_rejects_invalid_priority() -> None:
    response = client.post(
        "/assist",
        json={
            "event_id": "evt-1",
            "ticket_id": "T-1",
            "tenant_id": "tenant-a",
            "title": "物流咨询",
            "customer_message": "物流一直没有更新",
            "priority": "CRITICAL",
        },
    )

    assert response.status_code == 422
