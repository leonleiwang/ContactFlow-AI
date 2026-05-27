from __future__ import annotations

import re
import time

from app.knowledge_base import InMemoryKnowledgeBase, RetrievalHit
from app.models import AssistResult, Intent, Route, SlaRisk, TicketEvent


class AssistEngine:
    def __init__(self, knowledge_base: InMemoryKnowledgeBase | None = None) -> None:
        self.knowledge_base = knowledge_base or InMemoryKnowledgeBase()

    def analyze(self, event: TicketEvent) -> AssistResult:
        started = time.perf_counter()
        text = f"{event.title} {event.customer_message}"
        intent = self.detect_intent(text)
        handoff_reason = self.evaluate_handoff(text, intent, event.priority)
        sla_risk = self.evaluate_sla_risk(text, event.priority)
        route, hits = self.route(event, intent, handoff_reason)
        summary = self.summarize(event, intent)
        reply, confidence = self.suggest_reply(event, intent, route, hits, handoff_reason)
        latency_ms = int((time.perf_counter() - started) * 1000)

        return AssistResult(
            ticket_id=event.ticket_id,
            source_event_id=event.event_id,
            intent=intent,
            summary=summary,
            suggested_reply=reply,
            handoff_recommended=handoff_reason is not None,
            handoff_reason=handoff_reason,
            sla_risk=sla_risk,
            confidence=confidence,
            route=route,
            citations=[
                {"chunkId": hit.chunk.chunk_id, "title": hit.chunk.title, "score": round(hit.score, 4)}
                for hit in hits
            ],
            latency_ms=latency_ms,
            estimated_cost_usd=0.0 if route == Route.RULE_ONLY else 0.0002,
        )

    def detect_intent(self, text: str) -> Intent:
        normalized = text.lower()
        # 风险类意图优先级高于普通业务分类。客户同时提到“物流”和“投诉”时，
        # 系统应先保护服务风险，而不是把它当作普通物流咨询。
        if self._has_any(normalized, ["投诉", "差评", "律师", "监管", "complaint"]):
            return Intent.COMPLAINT
        if self._has_any(normalized, ["退款", "退货", "refund"]):
            return Intent.REFUND
        if self._has_any(normalized, ["物流", "快递", "没到", "delivery", "late"]):
            return Intent.DELIVERY
        if self._has_any(normalized, ["账单", "发票", "billing", "invoice"]):
            return Intent.BILLING
        if self._has_any(normalized, ["报错", "登录不了", "bug", "error"]):
            return Intent.TECHNICAL
        return Intent.GENERAL

    def evaluate_handoff(self, text: str, intent: Intent, priority: str) -> str | None:
        normalized = text.lower()
        if intent == Intent.COMPLAINT:
            return "投诉或监管风险需要人工介入"
        if priority.upper() == "URGENT":
            return "紧急优先级需要人工确认"
        if self._has_any(normalized, ["律师", "起诉", "监管", "媒体", "曝光", "vip"]):
            return "高风险关键词需要人工处理"
        return None

    def evaluate_sla_risk(self, text: str, priority: str) -> SlaRisk:
        normalized = text.lower()
        if priority.upper() == "URGENT" or self._has_any(normalized, ["投诉", "监管", "起诉"]):
            return SlaRisk.HIGH
        if priority.upper() == "HIGH" or self._has_any(normalized, ["超过", "一直", "多次"]):
            return SlaRisk.MEDIUM
        return SlaRisk.LOW

    def route(self, event: TicketEvent, intent: Intent, handoff_reason: str | None) -> tuple[Route, list[RetrievalHit]]:
        if handoff_reason:
            return Route.HANDOFF, []
        if intent in {Intent.REFUND, Intent.DELIVERY}:
            hits = self.knowledge_base.search(event.tenant_id, event.customer_message, intent=intent)
            return Route.RAG, hits
        return Route.RULE_ONLY, []

    def summarize(self, event: TicketEvent, intent: Intent) -> str:
        clean = re.sub(r"\s+", " ", event.customer_message).strip()
        return f"客户问题类型为 {intent.value}，核心诉求：{clean[:120]}"

    def suggest_reply(self, event: TicketEvent, intent: Intent, route: Route, hits: list[RetrievalHit], handoff_reason: str | None) -> tuple[str, float]:
        if route == Route.HANDOFF:
            return (
                f"建议转人工处理。原因：{handoff_reason}。可先安抚客户并确认订单、联系方式和期望解决方式。",
                0.42,
            )
        if route == Route.RAG:
            if not hits:
                # 证据不足时不生成确定政策答案，避免把“看起来合理”的文本当成事实。
                return (
                    "当前知识库没有找到足够依据。建议坐席先确认订单信息，并转入人工核查或补充知识库。",
                    0.35,
                )
            evidence = hits[0].chunk.text
            return (
                f"可以这样回复：您好，我们已收到您的问题。根据当前政策：{evidence} 我会继续为您核对具体订单情况。",
                0.78,
            )
        return (
            "可以这样回复：您好，我们已收到您的问题。请您补充订单号或更多细节，我会继续协助处理。",
            0.66,
        )

    @staticmethod
    def _has_any(text: str, keywords: list[str]) -> bool:
        return any(keyword in text for keyword in keywords)
