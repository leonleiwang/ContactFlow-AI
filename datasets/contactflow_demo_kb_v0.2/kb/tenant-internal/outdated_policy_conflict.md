---
tenant_id: tenant-internal
doc_id: tenant-internal/outdated_policy_conflict.md
title: 内部样本 过期政策与冲突识别
status: published
effective_from: 2026-01-01
acl_tags: ["support"]
---

# 内部样本 过期政策与冲突识别

## 样本说明
本文件用于测试过期政策识别，不作为正式客服答案依据。旧版数码退款政策曾允许签收 15 天内无理由退货，但该规则已于 2026-01-01 失效。

## 冲突处理
当检索同时命中新旧政策时，应优先使用生效日期最新且状态为 published 的文档。若无法判断版本，应提示证据冲突并转人工确认。

## 评估用途
评估集会使用本文件测试系统是否能识别过期政策、避免把旧政策当作最终答案。
