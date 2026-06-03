# ContactFlow AI V0.3 边界行为说明

展示说明：本文档用于面试展示和版本发布前检查，集中说明系统在模型不可用、证据不足、租户隔离、并发抢单和前端演示降级场景下的预期行为。

## LLM 不可用

触发条件：

- `LLM_ENABLED=false`
- 未配置 `DASHSCOPE_API_KEY` 或 `LLM_API_KEY`
- Qwen3-Max 超时、限流、5xx、网络不可达
- 备用模型 qwen-plus 也失败
- 返回内容不是可解析 JSON

预期行为：

- `/assist` 不报 500。
- 返回 `generationMode=template_fallback`。
- 返回明确 `degradedReason`。
- `summary` 和 `suggestedReply` 使用规则引擎预先生成的安全模板。
- 前端仍可展示 Assist 面板，失败工单可点击重试并使用 mock fallback。

## Rerank 不可用

触发条件：

- `RERANK_ENABLED=false`
- 未配置 `DASHSCOPE_API_KEY`、`RERANK_API_KEY` 或 `LLM_API_KEY`
- qwen3-rerank 超时、网络错误、返回分数数量不一致、返回结构异常

预期行为：

- `/rag/query` 不报 500。
- 保留本地轻量重排序结果。
- trace 返回 `rerank_mode=lightweight`。
- trace 返回 `rerank_degraded_reason`，便于前端和评估报告展示。

## 无充分证据

触发条件：

- 混合召回没有命中文档。
- top hit 分数不足。
- 用户提出知识库未授权权益，例如终身免费会员、无限补偿。

预期行为：

- `should_handoff=true`。
- `fallback_reason=no_sufficient_evidence`。
- 答案不编造政策，不承诺退款、赔偿或权益。
- citations 只保留转人工、知识更新、租户隔离等内部 SOP。

## 高风险投诉

触发条件：

- 命中投诉、起诉、律师、监管、媒体曝光、赔偿、精神损失等关键词。

预期行为：

- `should_handoff=true`。
- `fallback_reason=high_risk_handoff`。
- 优先召回内部高风险投诉 SOP。
- 答案只提供坐席处置建议，不自动承诺赔偿、退款或法律结论。

## 租户隔离

触发条件：

- 请求 `tenant-a` 时，问题文本提到 `tenant-b` 政策。
- RAG 候选文档包含其他业务租户内容。

预期行为：

- citations 只能包含当前业务租户和 `tenant-internal`。
- `tenant_leak_count=0`。
- 内部 SOP 可跨业务租户使用，因为它属于平台治理知识。

## Query Rewrite 漂移

触发条件：

- rewrite 候选丢失关键实体、业务意图或语义相似度不足。

预期行为：

- 候选进入 `rejected_rewrites`。
- reason 标记为 `semantic_drift`。
- 检索只使用原始问题和被接受的 rewrite。

## 并发抢单

触发条件：

- 多个坐席同时领取同一张 OPEN 工单。

预期行为：

- Redis 可选削峰锁减少并发冲突。
- MySQL 条件更新仍是最终事实。
- 已被领取时返回 `409 TICKET_STATE_CONFLICT`。
- 前端可展示“模拟抢单冲突”，用于面试说明并发设计。

## AI Assist 回写幂等

触发条件：

- RabbitMQ 重试。
- AI Service 或本地测试重复提交同一个 `sourceEventId`。

预期行为：

- Redis 短期去重减少重复处理。
- 数据库唯一键是最终幂等事实。
- 重复消息不会产生重复 AI Assist 记录。

## 前端 mock 与真实模型共存

预期行为：

- 20 条工单覆盖物流、退款、售后、发票、订阅、跨境、投诉、无证据、主管升级等场景。
- 前端 mock 是明确的演示降级层，不等同于生产数据。
- 真实 LLM 接入后，右侧 Assist 可由真实结果替换。
- 真实模型失败时仍可展示 mock/degraded/failed 三种状态，面试现场不会因为 API 失败而无法演示。
- 工单列表内部滚动，页面不会因工单数量增加而无限拉长。

## 发布前人工检查清单

- 前端三栏布局在 20 条工单下不撑爆页面。
- “采纳建议”能把 suggested reply 写入回复框。
- “发送回复”能追加本地会话。
- 失败 Assist 能重试到 fallback 状态。
- `/health` 返回 `version=0.3.0`。
- `/rag/query` 对 `top_k=50` 返回 422。
- `/assist` 对非法 priority 返回 422。
- 后端抢单冲突返回 409，而不是 500。
- RAG 高风险和无证据场景不输出确定性承诺。
