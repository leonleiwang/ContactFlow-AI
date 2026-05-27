---
tenant_id: tenant-internal
doc_id: tenant-internal/agent_assist_trace_sop.md
title: 内部 SOP AI Assist Trace 记录规范
status: published
effective_from: 2026-01-01
acl_tags: ["support"]
---

# 内部 SOP AI Assist Trace 记录规范

## Trace 字段
AI Assist 每次检索需要记录 originalQuery、acceptedRewrites、rejectedRewrites、retrievalStrategy、retrievedChunks、rerankScores、finalContext、citations、latencyMs 和 fallbackReason。

## 追溯要求
坐席或主管查看答案时，必须能看到证据来源、分数和低置信原因。无证据回答不得伪造引用，必须显示转人工或补充知识库建议。

## 运营用途
Trace 用于分析未命中问题、rewrite 噪音、重排序失败和知识库过期问题。运营人员可根据 trace 决定是否新增 FAQ 或调整 SOP。
