from app.models import Intent, KnowledgeChunk
from app.rag import DynamicChunker, HybridRetriever, QueryRewriter, RagEvaluator, RetrievalStrategy


def test_dynamic_chunker_preserves_markdown_structure_and_overlap() -> None:
    content = """
# 售后政策

## 退款
签收 7 天内且商品未使用，可以申请退款。超过 7 天需要人工审核。赠品需要一并退回。
如果客户已经拆封但没有使用，需要坐席记录原因。

## 物流
物流超过承诺时间 48 小时仍未更新时，应先查询物流轨迹。
"""
    chunker = DynamicChunker(max_tokens=18, overlap_tokens=6)

    chunks = chunker.split_markdown(
        content,
        tenant_id="tenant-a",
        doc_id="policy-v1",
        source_uri="manual://policy-v1",
        acl_tags={"support"},
    )

    assert len(chunks) >= 2
    assert chunks[0].section_path == ("售后政策", "退款")
    assert chunks[0].parent_id == "policy-v1:section:0"
    assert chunks[0].checksum
    assert chunks[0].acl_tags == {"support"}


def test_query_rewrite_discards_semantic_drift() -> None:
    rewriter = QueryRewriter(similarity_threshold=0.8)

    candidates = rewriter.rewrite("我想申请退款", Intent.REFUND)

    accepted = [candidate for candidate in candidates if candidate.accepted]
    rejected = [candidate for candidate in candidates if not candidate.accepted]
    assert accepted
    assert any("退款" in candidate.text for candidate in accepted)
    assert any(candidate.reason == "semantic_drift" for candidate in rejected)


def test_hybrid_retriever_combines_vector_bm25_and_tenant_filtering() -> None:
    chunks = [
        KnowledgeChunk(
            chunk_id="refund",
            tenant_id="tenant-a",
            title="退货退款 FAQ",
            text="签收 7 天内且商品未使用，可以申请退款。",
            tags={"refund", "faq"},
        ),
        KnowledgeChunk(
            chunk_id="delivery",
            tenant_id="tenant-a",
            title="物流手册",
            text="物流超过承诺时间 48 小时仍未更新时，应先查询物流轨迹。",
            tags={"delivery", "manual"},
        ),
        KnowledgeChunk(
            chunk_id="other-tenant",
            tenant_id="tenant-b",
            title="退款政策",
            text="tenant-b 的退款资料不允许被 tenant-a 召回。",
            tags={"refund"},
        ),
    ]
    retriever = HybridRetriever(chunks)

    hits = retriever.retrieve(
        "我想申请退款 refund policy",
        tenant_id="tenant-a",
        intent=Intent.REFUND,
        strategy=RetrievalStrategy.STANDARD,
    )

    assert hits
    assert hits[0].chunk.chunk_id == "refund"
    assert "bm25" in hits[0].matched_by
    assert all(hit.chunk.tenant_id == "tenant-a" for hit in hits)


def test_rag_evaluator_reports_recall_faithfulness_and_hallucination_risk() -> None:
    chunk = KnowledgeChunk(
        chunk_id="refund",
        tenant_id="tenant-a",
        title="退款政策",
        text="签收 7 天内且商品未使用，可以申请退款。",
        tags={"refund"},
    )
    hit = HybridRetriever([chunk]).retrieve("退款", tenant_id="tenant-a", intent=Intent.REFUND)[0]
    evaluator = RagEvaluator()

    metrics = evaluator.evaluate(
        required_terms={"签收", "退款"},
        answer="签收 7 天内且商品未使用，可以申请退款。",
        answer_claims=["支持 7 天内退款"],
        citations=[{"chunkId": "refund"}],
        hits=[hit],
    )

    assert metrics.context_recall == 1.0
    assert metrics.faithfulness > 0.5
    assert metrics.citation_coverage == 1.0
    assert metrics.hallucination_risk < 0.5
