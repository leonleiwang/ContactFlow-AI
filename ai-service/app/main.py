# 展示说明：AI Service 入口聚合规则引擎与 V0.2 RAG 查询能力，对外提供健康检查、坐席辅助和可追溯检索 API。
from __future__ import annotations

import json

from fastapi import FastAPI
from pydantic import BaseModel
from starlette.responses import JSONResponse

from app.engine import AssistEngine
from app.models import TicketEvent
from app.rag.query_engine import RagQueryEngine


# UTF-8 JSON 响应用于保证中文答案、证据引用和 trace 数据在 API 返回中不被转义，便于前端直接展示。
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


# 坐席辅助请求模型：承接工单事件中的租户、标题、客户消息和优先级，驱动规则引擎生成建议。
class TicketEventRequest(BaseModel):
    event_id: str
    ticket_id: str
    tenant_id: str
    title: str
    customer_message: str
    priority: str = "NORMAL"


# RAG 查询请求模型：限定租户、问题和 top_k，用于验证多租户隔离与可追溯召回链路。
class RagQueryRequest(BaseModel):
    tenant: str
    query: str
    top_k: int = 5


@app.get("/health")
# 健康检查接口：用于容器编排和本地演示确认 AI Service 已启动。
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/assist")
# 坐席辅助接口：输出意图、摘要、建议回复、转人工、SLA 风险、引用和成本等完整 AI Assist 结果。
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
# V0.2 可追溯 RAG 查询接口：返回答案、citations、fallback 决策、rewrite/recall/rerank/metrics trace。
def query_rag(request: RagQueryRequest) -> dict:
    return rag_engine.query(tenant=request.tenant, query=request.query, top_k=request.top_k)
