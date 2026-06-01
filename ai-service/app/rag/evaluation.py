# 展示说明：V0.2 RAG 评估模块，计算 Context Recall、Faithfulness、Citation Coverage 和幻觉风险等可运营指标。
from __future__ import annotations

from dataclasses import dataclass

from app.rag.embedding import tokenize
from app.rag.retrieval import HybridHit


@dataclass(frozen=True)
# 单次 RAG 查询指标：用于 API trace、批量评估报告和前端 Evidence Trace 面板统一展示。
class RagMetrics:
    context_recall: float
    faithfulness: float
    citation_coverage: float
    hallucination_risk: float


class RagEvaluator:
    def context_recall(self, required_terms: set[str], hits: list[HybridHit]) -> float:
        # Context Recall：检查期望证据关键词是否出现在召回上下文中，衡量召回覆盖度。
        if not required_terms:
            return 1.0
        context = " ".join(hit.chunk.text for hit in hits).lower()
        found = sum(1 for term in required_terms if term.lower() in context)
        return found / len(required_terms)

    def faithfulness(self, answer: str, hits: list[HybridHit]) -> float:
        # Faithfulness：用答案词项与证据上下文重合度近似衡量答案是否受证据支持。
        answer_terms = set(tokenize(answer))
        if not answer_terms:
            return 1.0
        context_terms = set(tokenize(" ".join(hit.chunk.text for hit in hits)))
        supported = answer_terms & context_terms
        return len(supported) / len(answer_terms)

    def citation_coverage(self, answer_claims: list[str], citations: list[dict]) -> float:
        # Citation Coverage：确保每类答案声明都有足够引用支撑，降低无出处回复。
        if not answer_claims:
            return 1.0
        if not citations:
            return 0.0
        return min(len(citations) / len(answer_claims), 1.0)

    def evaluate(
        self,
        *,
        required_terms: set[str],
        answer: str,
        answer_claims: list[str],
        citations: list[dict],
        hits: list[HybridHit],
    ) -> RagMetrics:
        # 聚合评估：一次性产出可落盘、可展示、可回归比较的 RAG 指标。
        context_recall = self.context_recall(required_terms, hits)
        faithfulness = self.faithfulness(answer, hits)
        citation_coverage = self.citation_coverage(answer_claims, citations)
        hallucination_risk = 1.0 - min(faithfulness, citation_coverage)
        return RagMetrics(
            context_recall=context_recall,
            faithfulness=faithfulness,
            citation_coverage=citation_coverage,
            hallucination_risk=hallucination_risk,
        )
