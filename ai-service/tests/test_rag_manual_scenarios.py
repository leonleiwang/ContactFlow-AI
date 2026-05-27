from app.rag.query_engine import RagQueryEngine


def test_manual_refund_quality_question_recalls_refund_and_warranty_documents() -> None:
    engine = RagQueryEngine()

    result = engine.query(
        tenant="tenant-a",
        query="我签收 8 天了，耳机有质量问题还能退吗？",
        top_k=5,
    )

    doc_ids = {citation["doc_id"] for citation in result["citations"]}
    assert "tenant-a/refund_policy.md" in doc_ids
    assert "tenant-a/warranty_policy.md" in doc_ids
    assert result["should_handoff"] is False
    assert result["fallback_reason"] is None


def test_manual_lawsuit_compensation_question_is_high_risk_handoff() -> None:
    engine = RagQueryEngine()

    result = engine.query(
        tenant="tenant-a",
        query="你们必须赔我 5000，不然我起诉。",
        top_k=5,
    )

    doc_ids = {citation["doc_id"] for citation in result["citations"]}
    assert result["trace"]["intent"] == "complaint"
    assert result["should_handoff"] is True
    assert result["fallback_reason"] == "high_risk_handoff"
    assert "tenant-internal/high_risk_complaint_sop.md" in doc_ids


def test_manual_lifetime_free_membership_uses_no_evidence_fallback() -> None:
    engine = RagQueryEngine()

    result = engine.query(
        tenant="tenant-a",
        query="你们能不能给我终身免费会员？",
        top_k=5,
    )

    assert result["should_handoff"] is True
    assert result["fallback_reason"] == "no_sufficient_evidence"
    assert "没有找到足够证据" in result["answer"]


def test_manual_tenant_a_query_does_not_recall_tenant_b_policy() -> None:
    engine = RagQueryEngine()

    result = engine.query(
        tenant="tenant-a",
        query="我是 tenant-a 的客户，想问 tenant-b 跨境 30 天退货政策",
        top_k=5,
    )

    citation_tenants = {citation["tenant"] for citation in result["citations"]}
    assert "tenant-b" not in citation_tenants
    assert citation_tenants <= {"tenant-a", "tenant-internal"}
    assert result["trace"]["metrics"]["tenant_leak_count"] == 0
