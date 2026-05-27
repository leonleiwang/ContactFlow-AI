---
tenant_id: tenant-internal
doc_id: tenant-internal/rag_evaluation_guideline.md
title: 内部 SOP RAG 评估指标说明
status: published
effective_from: 2026-01-01
acl_tags: ["support"]
---

# 内部 SOP RAG 评估指标说明

## 检索指标
Context Recall 衡量标准答案所需证据是否出现在召回上下文中。Tenant Leak Count 衡量是否召回了其他租户资料。Retrieval Latency 用于控制坐席体验。

## 生成指标
Faithfulness 衡量回答是否被上下文支持。Citation Coverage 衡量关键结论是否带引用。Hallucination Risk 在证据不足或回答越过证据时升高。

## 业务指标
首轮解决率、转人工率、坐席采纳率、坐席修改率和未命中问题沉淀，是判断系统是否可运营的核心指标。
