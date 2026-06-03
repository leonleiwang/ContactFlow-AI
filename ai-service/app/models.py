# 展示说明：AI Service 领域模型集中定义意图、路由、SLA 风险、工单事件、知识 chunk 和 V0.3 AI Assist 返回结果。
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Intent(str, Enum):
    # 客服意图枚举：驱动规则路由、RAG 检索策略和评估标签。
    REFUND = "refund"
    DELIVERY = "delivery"
    COMPLAINT = "complaint"
    BILLING = "billing"
    TECHNICAL = "technical"
    GENERAL = "general"


class SlaRisk(str, Enum):
    # SLA 风险等级：用于坐席台提示和后端审计事件。
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Route(str, Enum):
    # AI Assist 路由：区分纯规则、RAG 增强和人工介入三种处理路径。
    RULE_ONLY = "rule_only"
    RAG = "rag"
    HANDOFF = "handoff"


@dataclass(frozen=True)
# 工单事件输入：对应后端 ticket.created 事件传入 AI Service 的核心字段。
class TicketEvent:
    event_id: str
    ticket_id: str
    tenant_id: str
    title: str
    customer_message: str
    priority: str = "NORMAL"


@dataclass(frozen=True)
# 知识库 chunk：携带租户、章节路径、父 chunk、ACL、checksum 等可追溯检索元数据。
class KnowledgeChunk:
    chunk_id: str
    tenant_id: str
    title: str
    text: str
    tags: set[str] = field(default_factory=set)
    doc_id: str | None = None
    section_path: tuple[str, ...] = field(default_factory=tuple)
    source_uri: str | None = None
    parent_id: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    acl_tags: set[str] = field(default_factory=set)
    checksum: str | None = None


@dataclass(frozen=True)
# AI Assist 输出：封装摘要、建议回复、转人工、引用、耗时、成本和模型降级状态，供后端幂等落库。
class AssistResult:
    ticket_id: str
    source_event_id: str
    intent: Intent
    summary: str
    suggested_reply: str
    handoff_recommended: bool
    handoff_reason: str | None
    sla_risk: SlaRisk
    confidence: float
    route: Route
    citations: list[dict[str, Any]]
    latency_ms: int
    estimated_cost_usd: float
    generation_mode: str = "template"
    model_name: str | None = None
    degraded_reason: str | None = None
