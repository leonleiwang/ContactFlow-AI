from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Intent(str, Enum):
    REFUND = "refund"
    DELIVERY = "delivery"
    COMPLAINT = "complaint"
    BILLING = "billing"
    TECHNICAL = "technical"
    GENERAL = "general"


class SlaRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Route(str, Enum):
    RULE_ONLY = "rule_only"
    RAG = "rag"
    HANDOFF = "handoff"


@dataclass(frozen=True)
class TicketEvent:
    event_id: str
    ticket_id: str
    tenant_id: str
    title: str
    customer_message: str
    priority: str = "NORMAL"


@dataclass(frozen=True)
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
