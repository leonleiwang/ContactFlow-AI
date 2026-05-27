from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from app.engine import AssistEngine
from app.models import TicketEvent

app = FastAPI(title="ContactFlow AI Service", version="0.1.0")
engine = AssistEngine()


class TicketEventRequest(BaseModel):
    event_id: str
    ticket_id: str
    tenant_id: str
    title: str
    customer_message: str
    priority: str = "NORMAL"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/assist")
def create_assist(request: TicketEventRequest) -> dict:
    result = engine.analyze(
        TicketEvent(
            event_id=request.event_id,
            ticket_id=request.ticket_id,
            tenant_id=request.tenant_id,
            title=request.title,
            customer_message=request.customer_message,
            priority=request.priority,
        )
    )
    return {
        "ticketId": result.ticket_id,
        "sourceEventId": result.source_event_id,
        "intent": result.intent.value,
        "summary": result.summary,
        "suggestedReply": result.suggested_reply,
        "handoffRecommended": result.handoff_recommended,
        "handoffReason": result.handoff_reason,
        "slaRisk": result.sla_risk.value,
        "confidence": result.confidence,
        "route": result.route.value,
        "citations": result.citations,
        "latencyMs": result.latency_ms,
        "estimatedCostUsd": result.estimated_cost_usd,
    }
