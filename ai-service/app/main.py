from __future__ import annotations

import json

from fastapi import FastAPI
from pydantic import BaseModel
from starlette.responses import JSONResponse

from app.engine import AssistEngine
from app.models import TicketEvent
from app.rag.query_engine import RagQueryEngine


class Utf8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"

    def render(self, content: object) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")


app = FastAPI(title="ContactFlow AI Service", version="0.2.0", default_response_class=Utf8JSONResponse)
engine = AssistEngine()
rag_engine = RagQueryEngine()


class TicketEventRequest(BaseModel):
    event_id: str
    ticket_id: str
    tenant_id: str
    title: str
    customer_message: str
    priority: str = "NORMAL"


class RagQueryRequest(BaseModel):
    tenant: str
    query: str
    top_k: int = 5


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


@app.post("/rag/query")
def query_rag(request: RagQueryRequest) -> dict:
    return rag_engine.query(tenant=request.tenant, query=request.query, top_k=request.top_k)
