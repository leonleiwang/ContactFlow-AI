---
tenant_id: tenant-internal
doc_id: tenant-internal/handoff_routing_sop.md
title: 内部 SOP 转人工与派单规则
status: published
effective_from: 2026-01-01
acl_tags: ["support"]
---

# 内部 SOP 转人工与派单规则

## 转人工条件
低置信度、无证据、政策冲突、高风险投诉、VIP 客户、多次追问未解决、客户要求主管时，应转人工。AI 可以给出摘要和建议动作，但不能直接修改工单最终状态。

## 派单规则
普通售后进入一线坐席队列，跨境税费进入财务与清关队列，高风险投诉进入主管队列，法律威胁进入法务协同队列。派单事件需要记录 eventId 以支持幂等。

## 运营指标
系统需要统计转人工率、首轮解决率、AI 建议采纳率、未命中问题数和平均响应时延。
