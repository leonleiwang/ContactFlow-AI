# 展示说明：AI Assist 内存知识库适配层，复用 V0.2 混合检索能力为工单建议回复提供租户内证据。
from __future__ import annotations

from dataclasses import dataclass

from app.models import Intent, KnowledgeChunk
from app.rag.retrieval import HybridRetriever, RetrievalStrategy


@dataclass
# AI Assist 使用的检索命中结构：只暴露 chunk 和总分，保持规则引擎调用简单。
class RetrievalHit:
    chunk: KnowledgeChunk
    score: float


class InMemoryKnowledgeBase:
    """Tenant-scoped knowledge base used by the AI assist flow.

    V0.2 keeps the store in memory for local tests, while the retrieval path
    already uses query rewrite, vector recall, BM25 recall, source bonuses and
    strategy routing. A production store can replace the chunk list without
    changing the engine contract.
    """

    def __init__(self, chunks: list[KnowledgeChunk] | None = None) -> None:
        # 初始化演示知识库：内置少量租户 A 售后/物流样例，也支持测试注入完整 chunk 集合。
        self._chunks = chunks or [
            KnowledgeChunk(
                chunk_id="refund-7d",
                tenant_id="tenant-a",
                title="7 天退货退款政策",
                text="签收 7 天内且商品未使用，可以申请退款。超过 7 天需要人工审核。",
                tags={"refund", "policy", "faq"},
                doc_id="policy-refund",
                section_path=("售后政策", "退款"),
            ),
            KnowledgeChunk(
                chunk_id="delivery-delay",
                tenant_id="tenant-a",
                title="物流延迟处理",
                text="物流超过承诺时间 48 小时仍未更新时，坐席应先查询物流轨迹，再给出补偿或升级建议。",
                tags={"delivery", "sla", "manual"},
                doc_id="manual-delivery",
                section_path=("物流手册", "延迟处理"),
            ),
        ]
        self._retriever = HybridRetriever(self._chunks)

    def search(
        self,
        tenant_id: str,
        query: str,
        limit: int = 3,
        intent: Intent = Intent.GENERAL,
        strategy: RetrievalStrategy | None = None,
    ) -> list[RetrievalHit]:
        # 租户内检索：调用混合召回器并裁剪结果数量，避免跨租户文档进入坐席建议。
        hits = self._retriever.retrieve(query, tenant_id=tenant_id, intent=intent, strategy=strategy)
        return [RetrievalHit(chunk=hit.chunk, score=hit.score) for hit in hits[:limit]]
