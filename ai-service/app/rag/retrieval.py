# 展示说明：V0.2 混合召回模块，融合向量相似度、BM25 关键词匹配、来源加权和租户隔离，支撑 FAQ/手册/SOP 多路召回。
from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import Enum

from app.models import Intent, KnowledgeChunk
from app.rag.embedding import HashingEmbeddingModel, cosine_similarity, tokenize
from app.rag.rewrite import QueryRewriter


class RetrievalStrategy(str, Enum):
    # 检索策略枚举：按问题复杂度在简单、标准和深度召回之间切换。
    SIMPLE = "simple"
    STANDARD = "standard"
    DEEP = "deep"


@dataclass(frozen=True)
# 混合召回命中：同时保留总分、向量分、BM25 分、来源加权和命中通道，方便 trace 展示。
class HybridHit:
    chunk: KnowledgeChunk
    score: float
    vector_score: float
    bm25_score: float
    source_bonus: float
    matched_by: tuple[str, ...]


class BM25Index:
    # 构建轻量 BM25 索引，用于本地可测的关键词精确召回。
    def __init__(self, chunks: list[KnowledgeChunk]) -> None:
        self.chunks = chunks
        self.documents = [tokenize(f"{chunk.title} {chunk.text} {' '.join(chunk.tags)}") for chunk in chunks]
        self.doc_freq: Counter[str] = Counter()
        for document in self.documents:
            self.doc_freq.update(set(document))
        self.avg_doc_len = sum(len(document) for document in self.documents) / max(len(self.documents), 1)

    def score(self, query: str, chunk_index: int) -> float:
        # 对单个 chunk 计算 BM25 分数，让长尾实体、订单术语和政策关键词更容易被召回。
        terms = tokenize(query)
        if not terms:
            return 0.0
        doc = self.documents[chunk_index]
        if not doc:
            return 0.0
        term_freq = Counter(doc)
        score = 0.0
        k1 = 1.5
        b = 0.75
        for term in terms:
            if term not in term_freq:
                continue
            idf = math.log(1 + (len(self.documents) - self.doc_freq[term] + 0.5) / (self.doc_freq[term] + 0.5))
            denominator = term_freq[term] + k1 * (1 - b + b * len(doc) / max(self.avg_doc_len, 1))
            score += idf * (term_freq[term] * (k1 + 1) / denominator)
        return score


class HybridRetriever:
    # 初始化混合检索器：预计算 chunk 向量，并为同一批 chunk 构建 BM25 索引。
    def __init__(
        self,
        chunks: list[KnowledgeChunk],
        embedding_model: HashingEmbeddingModel | None = None,
        query_rewriter: QueryRewriter | None = None,
    ) -> None:
        self.chunks = chunks
        self.embedding_model = embedding_model or HashingEmbeddingModel()
        self.query_rewriter = query_rewriter or QueryRewriter(self.embedding_model)
        self.bm25 = BM25Index(chunks)
        self.vectors = [
            self.embedding_model.embed(f"{chunk.title} {chunk.text} {' '.join(chunk.tags)}")
            for chunk in chunks
        ]

    def retrieve(
        self,
        query: str,
        *,
        tenant_id: str,
        intent: Intent,
        strategy: RetrievalStrategy | None = None,
    ) -> list[HybridHit]:
        # 混合召回主流程：先做 query rewrite，再按租户过滤，从向量和 BM25 两路召回后融合排序。
        strategy = strategy or self.choose_strategy(query, intent)
        queries = self.query_rewriter.accepted_queries(query, intent)
        candidate_limit = {
            RetrievalStrategy.SIMPLE: 3,
            RetrievalStrategy.STANDARD: 10,
            RetrievalStrategy.DEEP: 30,
        }[strategy]
        final_limit = 3 if strategy != RetrievalStrategy.DEEP else 5

        scored: dict[int, dict[str, float | set[str]]] = defaultdict(lambda: {"vector": 0.0, "bm25": 0.0, "matched": set()})
        for candidate_query in queries:
            query_vector = self.embedding_model.embed(candidate_query)
            vector_scores = []
            bm25_scores = []
            for index, chunk in enumerate(self.chunks):
                if chunk.tenant_id not in {tenant_id, "tenant-internal"}:
                    continue
                vector_scores.append((index, max(0.0, cosine_similarity(query_vector, self.vectors[index]))))
                bm25_scores.append((index, self.bm25.score(candidate_query, index)))
            for index, score in sorted(vector_scores, key=lambda item: item[1], reverse=True)[:candidate_limit]:
                if score <= 0:
                    continue
                scored[index]["vector"] = max(float(scored[index]["vector"]), score)
                cast = scored[index]["matched"]
                assert isinstance(cast, set)
                cast.add("vector")
            for index, score in sorted(bm25_scores, key=lambda item: item[1], reverse=True)[:candidate_limit]:
                if score <= 0:
                    continue
                scored[index]["bm25"] = max(float(scored[index]["bm25"]), score)
                cast = scored[index]["matched"]
                assert isinstance(cast, set)
                cast.add("bm25")

        hits: list[HybridHit] = []
        for index, values in scored.items():
            chunk = self.chunks[index]
            source_bonus = self._source_bonus(chunk, intent)
            vector_score = float(values["vector"])
            bm25_score = float(values["bm25"])
            matched = values["matched"]
            assert isinstance(matched, set)
            score = (0.62 * vector_score) + (0.28 * min(bm25_score, 5.0) / 5.0) + source_bonus
            hits.append(
                HybridHit(
                    chunk=chunk,
                    score=score,
                    vector_score=vector_score,
                    bm25_score=bm25_score,
                    source_bonus=source_bonus,
                    matched_by=tuple(sorted(matched)),
                )
            )
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:final_limit]

    def choose_strategy(self, query: str, intent: Intent) -> RetrievalStrategy:
        # 策略路由：投诉、长问题或实体密集问题走 deep，售后/物流/技术走 standard，其余走 simple。
        entities = sum(1 for token in tokenize(query) if any(char.isdigit() for char in token) or len(token) >= 8)
        if intent == Intent.COMPLAINT or entities >= 2 or len(tokenize(query)) >= 18:
            return RetrievalStrategy.DEEP
        if intent in {Intent.REFUND, Intent.DELIVERY, Intent.TECHNICAL}:
            return RetrievalStrategy.STANDARD
        return RetrievalStrategy.SIMPLE

    def _source_bonus(self, chunk: KnowledgeChunk, intent: Intent) -> float:
        # 来源加权：FAQ、政策、SOP 和意图匹配文档获得小幅加分，增强答案可解释性。
        tags = {tag.lower() for tag in chunk.tags}
        if "faq" in tags:
            return 0.08
        if intent == Intent.REFUND and "refund" in tags:
            return 0.06
        if intent == Intent.DELIVERY and "delivery" in tags:
            return 0.06
        if "manual" in tags or "sop" in tags:
            return 0.04
        return 0.0
