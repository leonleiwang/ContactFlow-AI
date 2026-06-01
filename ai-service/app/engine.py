# 展示说明：V0.1/V0.2 坐席辅助规则引擎，负责意图识别、转人工风控、SLA 风险、路由和建议回复。
from __future__ import annotations

import re
import time

from app.knowledge_base import InMemoryKnowledgeBase, RetrievalHit
from app.models import AssistResult, Intent, Route, SlaRisk, TicketEvent


class AssistEngine:
    # 初始化坐席辅助引擎：默认使用内存知识库，也允许测试注入替代知识源。
    def __init__(self, knowledge_base: InMemoryKnowledgeBase | None = None) -> None:
        self.knowledge_base = knowledge_base or InMemoryKnowledgeBase()

    def analyze(self, event: TicketEvent) -> AssistResult:
        # 主分析流程：从工单事件生成完整 AI Assist 结果，并记录引用、耗时和成本估算。
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
        # 意图识别：高风险投诉优先，其次识别退款、物流、账单、技术等客服场景。
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
        # 转人工判断：投诉、紧急优先级、法律/监管/媒体/VIP 关键词触发人工介入。
        normalized = text.lower()
        if intent == Intent.COMPLAINT:
            return "投诉或监管风险需要人工介入"
        if priority.upper() == "URGENT":
            return "紧急优先级需要人工确认"
        if self._has_any(normalized, ["律师", "起诉", "监管", "媒体", "曝光", "vip"]):
            return "高风险关键词需要人工处理"
        return None

    def evaluate_sla_risk(self, text: str, priority: str) -> SlaRisk:
        # SLA 风险评估：根据优先级和风险词给出 LOW/MEDIUM/HIGH 分层。
        normalized = text.lower()
        if priority.upper() == "URGENT" or self._has_any(normalized, ["投诉", "监管", "起诉"]):
            return SlaRisk.HIGH
        if priority.upper() == "HIGH" or self._has_any(normalized, ["超过", "一直", "多次"]):
            return SlaRisk.MEDIUM
        return SlaRisk.LOW

    def route(self, event: TicketEvent, intent: Intent, handoff_reason: str | None) -> tuple[Route, list[RetrievalHit]]:
        # 路由决策：高风险走 handoff，售后/物流走 RAG，其余低风险问题走规则回复。
        if handoff_reason:
            return Route.HANDOFF, []
        if intent in {Intent.REFUND, Intent.DELIVERY}:
            hits = self.knowledge_base.search(event.tenant_id, event.customer_message, intent=intent)
            return Route.RAG, hits
        return Route.RULE_ONLY, []

    def summarize(self, event: TicketEvent, intent: Intent) -> str:
        # 工单摘要：压缩客户原文并保留识别出的业务意图，供坐席快速扫读。
        clean = re.sub(r"\s+", " ", event.customer_message).strip()
        return f"客户问题类型为 {intent.value}，核心诉求：{clean[:120]}"

    def suggest_reply(self, event: TicketEvent, intent: Intent, route: Route, hits: list[RetrievalHit], handoff_reason: str | None) -> tuple[str, float]:
        # 回复建议：依据路由输出人工提示、RAG 证据回复或规则兜底回复，并给出置信度。
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
        # 关键词匹配工具：集中处理规则引擎中的中文和英文触发词。
        return any(keyword in text for keyword in keywords)
