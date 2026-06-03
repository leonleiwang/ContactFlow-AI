# ContactFlow AI V0.3 接口规范

展示说明：本文档定义 V0.3 本地演示和后续 GitHub 版本更新时使用的接口契约，重点约束请求字段、响应字段、错误码、幂等键和降级语义，避免出现“能跑但接口松散”的低质量实现。

## 通用约定

- 所有 JSON 使用 `UTF-8`。
- 生产链路禁止提交 `.env` 和真实 API Key，真实密钥只放本地环境。
- 租户字段统一使用 `tenant-[a-z0-9-]+` 格式。
- AI Service 对未知字段使用 `extra=forbid`，未知参数直接返回 `422`。
- 后端工单主链路以 MySQL 为事实来源，Redis、RabbitMQ、LLM 和 rerank 都不是最终一致性来源。

## AI Service

### GET `/health`

用途：健康检查和版本确认。

响应：

```json
{
  "status": "ok",
  "version": "0.3.0"
}
```

### POST `/assist`

用途：根据工单事件生成坐席辅助建议。真实 LLM 可选；未启用、缺少密钥、超时或返回异常时自动使用模板兜底。

请求字段：

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `event_id` | string | 必填，1-80 |
| `ticket_id` | string | 必填，1-80 |
| `tenant_id` | string | 必填，1-80，`tenant-*` |
| `title` | string | 必填，1-120 |
| `customer_message` | string | 必填，1-2000 |
| `priority` | string | `LOW`、`NORMAL`、`HIGH`、`URGENT`，默认 `NORMAL` |

核心响应字段：

| 字段 | 说明 |
| --- | --- |
| `intent` | 识别出的业务意图 |
| `summary` | 坐席摘要 |
| `suggestedReply` | 建议回复 |
| `handoffRecommended` | 是否建议转人工 |
| `slaRisk` | `LOW`、`MEDIUM`、`HIGH` |
| `route` | `rule_only`、`rag`、`handoff` |
| `citations` | 证据引用摘要 |
| `generationMode` | `llm` 或 `template_fallback` |
| `modelName` | 实际模型名，降级时为 `null` |
| `degradedReason` | `llm_disabled`、`missing_api_key`、`llm_timeout`、`llm_http_error:*`、`llm_invalid_response` |

错误：

- `422`: 字段缺失、租户格式非法、优先级非法、文本过长或存在未知字段。

### POST `/rag/query`

用途：执行可追溯 RAG 查询，返回答案、证据引用、fallback 决策、rewrite/recall/rerank/metrics trace。

请求字段：

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `tenant` | string | 必填，1-80，`tenant-*` |
| `query` | string | 必填，2-1000，不能纯空白 |
| `top_k` | integer | 1-10，默认 5 |

核心响应字段：

| 字段 | 说明 |
| --- | --- |
| `answer` | 基于证据或 fallback 的回答 |
| `citations` | 引用 chunk、文档、租户、分数和召回方式 |
| `should_handoff` | 是否建议转人工 |
| `fallback_reason` | `high_risk_handoff`、`no_sufficient_evidence` 或 `null` |
| `trace.original_query` | 原始问题 |
| `trace.accepted_rewrites` | 通过语义校验的 rewrite |
| `trace.rejected_rewrites` | 被拒绝的 rewrite 与原因 |
| `trace.retrieval_strategy` | `simple`、`standard`、`deep` |
| `trace.rerank_mode` | `model`、`lightweight`、`empty` |
| `trace.rerank_model` | 例如 `qwen3-rerank` |
| `trace.rerank_degraded_reason` | `rerank_disabled`、`missing_api_key`、`rerank_timeout`、`rerank_http_error`、`rerank_invalid_response` |
| `trace.metrics` | context recall、faithfulness、citation coverage、hallucination risk、tenant leak count 等 |

错误：

- `422`: `top_k` 越界、query 为空、租户格式非法或出现未知字段。

## Ticket Service

### POST `/api/tickets`

用途：创建工单，写入 MySQL，发布领域事件，触发异步 AI Assist。

请求字段：

| 字段 | 约束 |
| --- | --- |
| `tenantId` | 必填，最大 80，`tenant-*` |
| `title` | 必填，最大 120 |
| `customerName` | 必填，最大 80 |
| `customerMessage` | 必填，最大 2000 |
| `priority` | `LOW`、`NORMAL`、`HIGH`、`URGENT` |

错误：`400 VALIDATION_FAILED`。

### GET `/api/tickets?tenantId=tenant-a`

用途：按租户返回工单列表。租户隔离在服务层执行。

### GET `/api/tickets/{ticketId}?tenantId=tenant-a`

用途：读取单个工单详情。

错误：

- `404 TICKET_NOT_FOUND`: 工单不存在或不属于该租户。

### POST `/api/tickets/{ticketId}/claim`

用途：领取工单。Redis 可做削峰锁，MySQL 条件更新仍是最终事实。

请求字段：

| 字段 | 约束 |
| --- | --- |
| `tenantId` | 必填，最大 80，`tenant-*` |
| `agentId` | 必填，最大 80 |

错误：

- `409 TICKET_STATE_CONFLICT`: 已被其他坐席领取或状态不允许领取。

### POST `/api/tickets/{ticketId}/transitions`

用途：状态流转并记录审计事件。

请求字段：

| 字段 | 约束 |
| --- | --- |
| `tenantId` | 必填，最大 80，`tenant-*` |
| `actorId` | 必填，最大 80 |
| `targetStatus` | TicketStatus 枚举 |
| `reason` | 可选，最大 500 |

错误：

- `409 TICKET_STATE_CONFLICT`: 非法状态流转。

### POST `/api/ai-assists`

用途：模拟或接收 `ai.assist.completed` 回写，按 `sourceEventId` 幂等落库。

请求字段重点约束：

- `sourceEventId`: 必填，最大 120。
- `summary`: 必填，最大 1000。
- `suggestedReply`: 必填，最大 2000。
- `confidence`: 0.0-1.0。
- `citationsJson`: 最大 8000。
- `latencyMs`: 0-300000。
- `estimatedCostUsd`: 非负。

### GET `/api/tickets/{ticketId}/events`

用途：返回工单审计事件，用于展示创建、领取、流转和 AI Assist 挂载记录。

### GET `/api/tickets/{ticketId}/ai-assists`

用途：返回工单关联的 AI Assist 结果列表。

## 版本发布检查

发布 `v0.3.0` 前需要至少通过：

```powershell
cd ./frontend
npm run build
```

```powershell
cd ./ai-service
python -m pytest -p no:cacheprovider
```

```powershell
cd ./backend
mvn test
```
