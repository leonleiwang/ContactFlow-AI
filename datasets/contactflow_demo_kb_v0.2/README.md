# ContactFlow Demo Enterprise KB v0.2

This is a synthetic enterprise customer-support knowledge base for ContactFlow AI.
It is designed to test whether the RAG pipeline is operational, evaluable, and traceable.

## Contents

- Knowledge documents: 24 Markdown files
- Evaluation cases: 120 JSONL rows
- Tenants: tenant-a, tenant-b, tenant-internal

## Why Synthetic

The dataset follows the structure of real customer-support knowledge bases and enterprise RAG benchmarks,
but the policy content is fictional and written for ContactFlow AI. This keeps the project safe to publish
while still covering realistic support scenarios.

## Coverage

- Refund, exchange, warranty, invoice, delivery, lost package, compensation, preorder
- Cross-border shipping, tax, size exchange, custom home goods, damaged goods, subscription billing
- High-risk complaint, forbidden promises, handoff routing, knowledge update, RAG evaluation, tenant isolation
- Query rewrite drift, no-evidence fallback, multi-document reasoning, exact keyword recall

## Eval Schema

Each JSONL row includes:

- id
- type
- tenant
- question
- expected_intent
- expected_doc_ids
- expected_evidence_keywords
- should_answer
- should_handoff
- risk_level
