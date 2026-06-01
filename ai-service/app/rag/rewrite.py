# 展示说明：V0.2 Query Rewrite 模块，生成业务检索扩展词并用语义相似度校验，防止 rewrite drift。
from __future__ import annotations

from dataclasses import dataclass

from app.models import Intent
from app.rag.embedding import HashingEmbeddingModel, cosine_similarity, tokenize


@dataclass(frozen=True)
# Rewrite 候选记录：保留改写文本、相似度、是否采纳和拒绝原因，供 trace 与评估指标使用。
class RewriteCandidate:
    text: str
    similarity: float
    accepted: bool
    reason: str


class QueryRewriter:
    # 初始化改写器：复用 embedding 模型，并设置语义漂移拦截阈值。
    def __init__(
        self,
        embedding_model: HashingEmbeddingModel | None = None,
        similarity_threshold: float = 0.8,
    ) -> None:
        self.embedding_model = embedding_model or HashingEmbeddingModel()
        self.similarity_threshold = similarity_threshold

    def rewrite(self, query: str, intent: Intent) -> list[RewriteCandidate]:
        # 生成并校验改写候选：只有语义保持足够高的候选才进入后续混合召回。
        original = query.strip()
        original_embedding = self.embedding_model.embed(original)
        candidates = self._generate_candidates(original, intent)
        results: list[RewriteCandidate] = []
        for candidate in candidates:
            similarity = max(
                cosine_similarity(original_embedding, self.embedding_model.embed(candidate)),
                self._term_preservation(original, candidate),
            )
            accepted = similarity >= self.similarity_threshold
            results.append(
                RewriteCandidate(
                    text=candidate,
                    similarity=similarity,
                    accepted=accepted,
                    reason="semantic_match" if accepted else "semantic_drift",
                )
            )
        return results

    def accepted_queries(self, query: str, intent: Intent) -> list[str]:
        # 输出原始 query 与已通过校验的 rewrite query，保证召回扩展同时保留用户原意。
        accepted = [candidate.text for candidate in self.rewrite(query, intent) if candidate.accepted]
        return [query, *accepted]

    def _term_preservation(self, original: str, candidate: str) -> float:
        # 关键词保留率：作为轻量语义校验补充，防止改写丢失订单、政策或风险术语。
        original_terms = set(tokenize(original))
        if not original_terms:
            return 0.0
        candidate_terms = set(tokenize(candidate))
        return len(original_terms & candidate_terms) / len(original_terms)

    def _generate_candidates(self, query: str, intent: Intent) -> list[str]:
        # 按意图生成演示级改写候选，其中包含刻意漂移样本，用于测试 rewrite drift 拦截。
        if intent == Intent.COMPLAINT:
            return [query]
        if intent == Intent.REFUND:
            return [
                f"{query} 退款 退货 售后 政策",
                f"{query} 是否符合退货退款条件",
                "天气很好，推荐附近餐厅",
            ]
        if intent == Intent.DELIVERY:
            return [
                f"{query} 物流 延迟 快递 时效",
                f"{query} 查询物流异常处理规则",
                "请生成一首歌",
            ]
        return [query]
