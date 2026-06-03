# 展示说明：AI Service 入口聚合规则引擎、V0.3 LLM 降级链路与 RAG 查询能力，对外提供健康检查、坐席辅助和可追溯检索 API。
from __future__ import annotations

import json

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.responses import JSONResponse

from app.engine import AssistEngine
from app.models import TicketEvent
from app.rag.query_engine import RagQueryEngine


# UTF-8 JSON 响应用于保证中文答案、证据引用和 trace 数据在 API 返回中不被转义，便于前端直接展示。
class Utf8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"

    # 响应序列化：禁止 NaN 等非标准 JSON 值，确保接口返回能被前端、评估脚本和审计系统稳定解析。
    def render(self, content: object) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")


# FastAPI 应用元信息：版本号与 README、接口规范和候选 Git tag 保持一致，便于演示和发布核对。
app = FastAPI(title="ContactFlow AI Service", version="0.3.0", default_response_class=Utf8JSONResponse)
engine = AssistEngine()
rag_engine = RagQueryEngine()


# 坐席辅助请求模型：承接工单事件中的租户、标题、客户消息和优先级，驱动规则引擎与 LLM Provider 生成建议。
class TicketEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_id: str = Field(..., min_length=1, max_length=80)
    ticket_id: str = Field(..., min_length=1, max_length=80)
    tenant_id: str = Field(..., min_length=1, max_length=80, pattern=r"^tenant-[a-z0-9-]+$")
    title: str = Field(..., min_length=1, max_length=120)
    customer_message: str = Field(..., min_length=1, max_length=2000)
    priority: str = Field(default="NORMAL", pattern=r"^(LOW|NORMAL|HIGH|URGENT)$")


# RAG 查询请求模型：限定租户、问题和 top_k，用于验证多租户隔离、可追溯召回和 rerank 降级链路。
class RagQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    tenant: str = Field(..., min_length=1, max_length=80, pattern=r"^tenant-[a-z0-9-]+$")
    query: str = Field(..., min_length=2, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)

    # 查询归一化：拒绝纯空白问题，避免低质量请求进入 rewrite、召回和评估链路。
    @field_validator("query")
    @classmethod
    def reject_blank_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be blank")
        return value


@app.get("/health")
# 健康检查接口：用于容器编排和本地演示确认 AI Service 已启动。
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.3.0"}


@app.post("/assist")
# 坐席辅助接口：输出意图、摘要、建议回复、转人工、SLA 风险、引用、成本和 LLM 降级状态等完整结果。
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
        "generationMode": result.generation_mode,
        "modelName": result.model_name,
        "degradedReason": result.degraded_reason,
    }


@app.post("/rag/query")
# V0.3 可追溯 RAG 查询接口：返回答案、citations、fallback 决策、rewrite/recall/rerank/metrics trace。
def query_rag(request: RagQueryRequest) -> dict:
    return rag_engine.query(tenant=request.tenant, query=request.query, top_k=request.top_k)
