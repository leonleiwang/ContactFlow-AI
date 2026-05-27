from __future__ import annotations

from dataclasses import dataclass

from app.models import Intent
from app.rag.embedding import HashingEmbeddingModel, cosine_similarity, tokenize


@dataclass(frozen=True)
class RewriteCandidate:
    text: str
    similarity: float
    accepted: bool
    reason: str


class QueryRewriter:
    def __init__(
        self,
        embedding_model: HashingEmbeddingModel | None = None,
        similarity_threshold: float = 0.8,
    ) -> None:
        self.embedding_model = embedding_model or HashingEmbeddingModel()
        self.similarity_threshold = similarity_threshold

    def rewrite(self, query: str, intent: Intent) -> list[RewriteCandidate]:
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
        accepted = [candidate.text for candidate in self.rewrite(query, intent) if candidate.accepted]
        return [query, *accepted]

    def _term_preservation(self, original: str, candidate: str) -> float:
        original_terms = set(tokenize(original))
        if not original_terms:
            return 0.0
        candidate_terms = set(tokenize(candidate))
        return len(original_terms & candidate_terms) / len(original_terms)

    def _generate_candidates(self, query: str, intent: Intent) -> list[str]:
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
