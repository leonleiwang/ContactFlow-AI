from __future__ import annotations

from dataclasses import dataclass

from app.models import KnowledgeChunk


@dataclass
class RetrievalHit:
    chunk: KnowledgeChunk
    score: float


class InMemoryKnowledgeBase:
    """V0.1 只做轻量 RAG mock，但保留 tenant 过滤和证据返回。

    这里故意不让检索器跨租户返回内容：企业知识库首先要保证数据隔离，
    然后才是召回率和生成效果。
    """

    def __init__(self, chunks: list[KnowledgeChunk] | None = None) -> None:
        self._chunks = chunks or [
            KnowledgeChunk(
                chunk_id="refund-7d",
                tenant_id="tenant-a",
                title="7 天退款政策",
                text="签收 7 天内且商品未使用，可以申请退款。超过 7 天需要人工审核。",
                tags={"refund", "policy"},
            ),
            KnowledgeChunk(
                chunk_id="delivery-delay",
                tenant_id="tenant-a",
                title="物流延迟处理",
                text="物流超过承诺时间 48 小时仍未更新时，坐席应先查询物流轨迹，再给出补偿或升级建议。",
                tags={"delivery", "sla"},
            ),
        ]

    def search(self, tenant_id: str, query: str, limit: int = 3) -> list[RetrievalHit]:
        terms = {term.strip("，。,.!?").lower() for term in query.split() if term.strip()}
        hits: list[RetrievalHit] = []
        for chunk in self._chunks:
            if chunk.tenant_id != tenant_id:
                continue
            haystack = f"{chunk.title} {chunk.text} {' '.join(chunk.tags)}".lower()
            overlap = sum(1 for term in terms if term and term in haystack)
            if overlap:
                hits.append(RetrievalHit(chunk=chunk, score=overlap / max(len(terms), 1)))
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]
