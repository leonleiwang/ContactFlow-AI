---
tenant_id: tenant-internal
doc_id: tenant-internal/tenant_isolation_policy.md
title: 内部 SOP 多租户知识隔离规则
status: published
effective_from: 2026-01-01
acl_tags: ["support"]
---

# 内部 SOP 多租户知识隔离规则

## 基本原则
每条知识、chunk、评估问题和回答 trace 必须带 tenant_id。检索时必须先做租户过滤，再做向量或 BM25 召回。内部 SOP 可以被授权坐席使用，但不能泄露给客户。

## 风险场景
Tenant A 的 7 天数码退款政策不能回答 Tenant B 的跨境服饰 30 天退货问题。Tenant B 的税费规则不能回答 Tenant A 的国内数码订单。跨租户命中应计为严重检索错误。

## 审计
每次召回需要记录 tenant_id、doc_id、chunk_id、ACL tag 和调用用户角色，方便排查数据泄漏。
