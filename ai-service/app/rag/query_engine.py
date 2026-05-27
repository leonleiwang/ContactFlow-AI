from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from app.models import Intent, KnowledgeChunk
from app.rag.chunker import DynamicChunker
from app.rag.embedding import HashingEmbeddingModel, tokenize
from app.rag.evaluation import RagEvaluator
from app.rag.retrieval import HybridHit, HybridRetriever, RetrievalStrategy
from app.rag.rewrite import QueryRewriter


HIGH_RISK_TERMS = {
    "起诉",
    "律师",
    "监管",
    "媒体",
    "曝光",
    "精神损失",
    "赔偿",
    "投诉",
    "必须赔",
}

UNSUPPORTED_ENTITLEMENT_TERMS = {
    "终身免费",
    "免费会员",
    "永久免费",
    "无限补偿",
}


class RagQueryEngine:
    def __init__(self, dataset_root: Path | None = None) -> None:
        self.dataset_root = dataset_root or self._default_dataset_root()
        self.embedding_model = HashingEmbeddingModel()
        self.rewriter = QueryRewriter(self.embedding_model)
        self.evaluator = RagEvaluator()
        self.chunker = DynamicChunker(max_tokens=180, overlap_tokens=80)
        self.chunks = self._load_chunks()
        self.retriever = HybridRetriever(self.chunks, self.embedding_model, self.rewriter)

    def query(
        self,
        *,
        tenant: str,
        query: str,
        top_k: int = 5,
        expected_doc_ids: list[str] | None = None,
        expected_evidence_keywords: list[str] | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        normalized_top_k = max(1, min(top_k, 10))
        intent = self._detect_intent(query)
        strategy = self._choose_strategy(query, intent, normalized_top_k)
        rewrite_candidates = self.rewriter.rewrite(query, intent)
        accepted_rewrites = [asdict(candidate) for candidate in rewrite_candidates if candidate.accepted]
        rejected_rewrites = [asdict(candidate) for candidate in rewrite_candidates if not candidate.accepted]

        hits = self.retriever.retrieve(query, tenant_id=tenant, intent=intent, strategy=strategy)
        reranked_hits = self._rerank(query, hits, intent)[:normalized_top_k]
        retrieval_latency_ms = int((time.perf_counter() - started) * 1000)

        citations = self._build_citations(reranked_hits)
        high_risk = self._is_high_risk(query)
        unsupported_entitlement = self._is_unsupported_entitlement(query)
        evidence_ok = self._has_enough_evidence(reranked_hits) and not unsupported_entitlement
        should_handoff, fallback_reason = self._decide_fallback(high_risk, evidence_ok, citations)
        answer = self._compose_answer(query, reranked_hits, should_handoff, fallback_reason)
        answer_claims = self._answer_claims(answer, should_handoff, citations)

        required_terms = set(expected_evidence_keywords or self._query_terms(query))
        metrics = self.evaluator.evaluate(
            required_terms=required_terms,
            answer=answer,
            answer_claims=answer_claims,
            citations=citations,
            hits=reranked_hits,
        )
        total_rewrites = len(rewrite_candidates)
        rewrite_accept_rate = len(accepted_rewrites) / total_rewrites if total_rewrites else 1.0
        tenant_leak_count = self._tenant_leak_count(tenant, citations)

        metrics_payload = {
            "context_recall": round(metrics.context_recall, 4),
            "faithfulness": round(metrics.faithfulness, 4),
            "citation_coverage": round(metrics.citation_coverage, 4),
            "hallucination_risk": round(metrics.hallucination_risk, 4),
            "rewrite_accept_rate": round(rewrite_accept_rate, 4),
            "retrieval_latency_ms": retrieval_latency_ms,
            "tenant_leak_count": tenant_leak_count,
        }

        if expected_doc_ids:
            retrieved_doc_ids = {citation["doc_id"] for citation in citations}
            metrics_payload["expected_doc_hit_rate"] = round(
                len(retrieved_doc_ids & set(expected_doc_ids)) / len(set(expected_doc_ids)),
                4,
            )

        return {
            "answer": answer,
            "citations": citations,
            "should_handoff": should_handoff,
            "fallback_reason": fallback_reason,
            "trace": {
                "original_query": query,
                "intent": intent.value,
                "accepted_rewrites": accepted_rewrites,
                "rejected_rewrites": rejected_rewrites,
                "retrieval_strategy": strategy.value,
                "retrieved_chunks": [self._hit_payload(hit) for hit in hits],
                "reranked_chunks": [self._hit_payload(hit) for hit in reranked_hits],
                "metrics": metrics_payload,
            },
        }

    def _load_chunks(self) -> list[KnowledgeChunk]:
        kb_root = self.dataset_root / "kb"
        if not kb_root.exists():
            raise FileNotFoundError(f"Demo knowledge base not found: {kb_root}")

        chunks: list[KnowledgeChunk] = []
        for path in sorted(kb_root.glob("*/*.md")):
            raw = path.read_text(encoding="utf-8")
            metadata, content = self._split_frontmatter(raw)
            tenant = metadata.get("tenant_id") or path.parent.name
            doc_id = metadata.get("doc_id") or f"{path.parent.name}/{path.name}"
            title = metadata.get("title") or path.stem
            source_uri = f"dataset://contactflow_demo_kb_v0.2/{doc_id}"
            tags = self._tags_for_document(doc_id, title, content)
            doc_chunks = self.chunker.split_markdown(
                content,
                tenant_id=tenant,
                doc_id=doc_id,
                source_uri=source_uri,
                acl_tags={"support"},
            )
            for chunk in doc_chunks:
                chunks.append(
                    replace(
                        chunk,
                        title=title if chunk.title == "root" else chunk.title,
                        tags=tags,
                        effective_from=metadata.get("effective_from"),
                    )
                )
        return chunks

    @staticmethod
    def _split_frontmatter(raw: str) -> tuple[dict[str, str], str]:
        if not raw.startswith("---"):
            return {}, raw
        parts = raw.split("---", 2)
        if len(parts) < 3:
            return {}, raw
        metadata: dict[str, str] = {}
        for line in parts[1].splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"')
        return metadata, parts[2].strip()

    @staticmethod
    def _tags_for_document(doc_id: str, title: str, content: str) -> set[str]:
        text = f"{doc_id} {title} {content}".lower()
        tags = {"manual"}
        if "sop" in text:
            tags.update({"sop", "manual"})
        if "faq" in text:
            tags.add("faq")
        mapping = {
            "refund": ["退款", "退货", "refund"],
            "delivery": ["物流", "签收", "丢件", "shipping", "delivery"],
            "billing": ["发票", "账单", "税费", "invoice", "billing", "tax"],
            "warranty": ["保修", "质检", "破损", "warranty", "damaged"],
            "complaint": ["投诉", "法律威胁", "监管", "complaint"],
            "handoff": ["转人工", "升级主管", "handoff"],
        }
        for tag, keywords in mapping.items():
            if any(keyword in text for keyword in keywords):
                tags.add(tag)
        return tags

    def _detect_intent(self, query: str) -> Intent:
        lowered = query.lower()
        if self._contains(lowered, ["起诉", "律师", "监管", "媒体", "曝光", "投诉", "complaint"]):
            return Intent.COMPLAINT
        if self._contains(lowered, ["退货", "退款", "退", "refund"]):
            return Intent.REFUND
        if self._contains(lowered, ["物流", "签收", "快递", "没收到", "丢件", "delivery", "shipping"]):
            return Intent.DELIVERY
        if self._contains(lowered, ["发票", "账单", "税费", "会员", "invoice", "billing", "tax"]):
            return Intent.BILLING
        if self._contains(lowered, ["保修", "质量", "破损", "维修", "warranty"]):
            return Intent.TECHNICAL
        return Intent.GENERAL

    def _choose_strategy(self, query: str, intent: Intent, top_k: int) -> RetrievalStrategy:
        if top_k >= 5 or self._is_high_risk(query):
            return RetrievalStrategy.DEEP
        return self.retriever.choose_strategy(query, intent)

    def _rerank(self, query: str, hits: list[HybridHit], intent: Intent) -> list[HybridHit]:
        query_tokens = set(tokenize(query))

        def score(hit: HybridHit) -> float:
            chunk_text = f"{hit.chunk.title} {hit.chunk.text} {' '.join(hit.chunk.tags)}"
            chunk_tokens = set(tokenize(chunk_text))
            exact_overlap = len(query_tokens & chunk_tokens) / max(len(query_tokens), 1)
            internal_risk_bonus = 0.12 if self._is_high_risk(query) and hit.chunk.tenant_id == "tenant-internal" else 0.0
            intent_bonus = 0.08 if intent.value in hit.chunk.tags else 0.0
            source_bonus = 0.05 if {"sop", "manual"} & hit.chunk.tags else 0.0
            return hit.score + exact_overlap + internal_risk_bonus + intent_bonus + source_bonus

        return sorted(
            [
                HybridHit(
                    chunk=hit.chunk,
                    score=score(hit),
                    vector_score=hit.vector_score,
                    bm25_score=hit.bm25_score,
                    source_bonus=hit.source_bonus,
                    matched_by=hit.matched_by,
                )
                for hit in hits
            ],
            key=lambda item: item.score,
            reverse=True,
        )

    def _has_enough_evidence(self, hits: list[HybridHit]) -> bool:
        if not hits:
            return False
        top = hits[0]
        if top.bm25_score > 0:
            return True
        return top.score >= 0.22 and top.vector_score >= 0.18

    def _decide_fallback(
        self,
        high_risk: bool,
        evidence_ok: bool,
        citations: list[dict[str, Any]],
    ) -> tuple[bool, str | None]:
        if high_risk:
            return True, "high_risk_handoff"
        if not evidence_ok or not citations:
            return True, "no_sufficient_evidence"
        return False, None

    def _compose_answer(
        self,
        query: str,
        hits: list[HybridHit],
        should_handoff: bool,
        fallback_reason: str | None,
    ) -> str:
        if fallback_reason == "high_risk_handoff":
            return (
                "已识别为高风险或投诉升级场景。系统只提供坐席处理建议：先安抚客户，确认订单、诉求和证据，"
                "创建升级工单，并由主管或法务协同处理；当前不会自动承诺退款、赔偿或处理结果。"
            )
        if fallback_reason == "no_sufficient_evidence":
            return (
                "当前知识库没有找到足够证据支持确定回答。建议坐席补充订单信息或转人工核查，"
                "并将该问题进入知识库补充池。"
            )
        if not hits:
            return "当前没有可引用证据，建议转人工核查。"

        snippets = []
        for hit in hits[:2]:
            snippets.append(self._compact_text(hit.chunk.text, 120))
        return "根据已召回的企业知识库证据：" + "；".join(snippets) + "。坐席回复时应保留审核边界，并引用对应政策来源。"

    def _build_citations(self, hits: list[HybridHit]) -> list[dict[str, Any]]:
        citations = []
        for hit in hits:
            citations.append(
                {
                    "chunk_id": hit.chunk.chunk_id,
                    "doc_id": hit.chunk.doc_id,
                    "title": hit.chunk.title,
                    "section_path": list(hit.chunk.section_path),
                    "source_uri": hit.chunk.source_uri,
                    "tenant": hit.chunk.tenant_id,
                    "score": round(hit.score, 4),
                    "matched_by": list(hit.matched_by),
                }
            )
        return citations

    def _hit_payload(self, hit: HybridHit) -> dict[str, Any]:
        return {
            "chunk_id": hit.chunk.chunk_id,
            "doc_id": hit.chunk.doc_id,
            "title": hit.chunk.title,
            "tenant": hit.chunk.tenant_id,
            "section_path": list(hit.chunk.section_path),
            "score": round(hit.score, 4),
            "vector_score": round(hit.vector_score, 4),
            "bm25_score": round(hit.bm25_score, 4),
            "source_bonus": round(hit.source_bonus, 4),
            "matched_by": list(hit.matched_by),
            "checksum": hit.chunk.checksum,
        }

    @staticmethod
    def _answer_claims(answer: str, should_handoff: bool, citations: list[dict[str, Any]]) -> list[str]:
        if not answer:
            return []
        if should_handoff:
            return ["handoff", "risk_control"]
        return ["policy_answer"] if citations else []

    @staticmethod
    def _query_terms(query: str) -> list[str]:
        return [token for token in tokenize(query) if len(token) > 1 or token.isdigit()]

    @staticmethod
    def _tenant_leak_count(tenant: str, citations: list[dict[str, Any]]) -> int:
        leaks = 0
        for citation in citations:
            citation_tenant = citation.get("tenant")
            if citation_tenant not in {tenant, "tenant-internal"}:
                leaks += 1
        return leaks

    @staticmethod
    def _is_high_risk(query: str) -> bool:
        lowered = query.lower()
        return any(term in lowered for term in HIGH_RISK_TERMS)

    @staticmethod
    def _is_unsupported_entitlement(query: str) -> bool:
        lowered = query.lower()
        return any(term in lowered for term in UNSUPPORTED_ENTITLEMENT_TERMS)

    @staticmethod
    def _contains(text: str, keywords: list[str]) -> bool:
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _compact_text(text: str, max_chars: int) -> str:
        normalized = re.sub(r"\s+", " ", text).strip()
        if len(normalized) <= max_chars:
            return normalized
        return normalized[: max_chars - 1] + "..."

    @staticmethod
    def _default_dataset_root() -> Path:
        return Path(__file__).resolve().parents[3] / "datasets" / "contactflow_demo_kb_v0.2"


def load_eval_cases(dataset_root: Path | None = None) -> list[dict[str, Any]]:
    root = dataset_root or RagQueryEngine._default_dataset_root()
    cases_path = root / "eval" / "eval_cases.jsonl"
    return [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines() if line.strip()]
