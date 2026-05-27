from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


DATASET = Path(__file__).resolve().parents[2] / "datasets" / "contactflow_demo_kb_v0.2"
KB = DATASET / "kb"
EVAL_CASES = DATASET / "eval" / "eval_cases.jsonl"


def load_cases() -> list[dict]:
    return [json.loads(line) for line in EVAL_CASES.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_demo_dataset_has_professional_scale_and_required_files() -> None:
    docs = list(KB.glob("*/*.md"))
    cases = load_cases()

    assert len(docs) == 24
    assert len(cases) == 120
    assert (DATASET / "README.md").exists()
    assert (DATASET / "eval" / "manifest.json").exists()


def test_eval_cases_have_required_schema_and_existing_evidence_docs() -> None:
    doc_ids = {f"{path.parent.name}/{path.name}" for path in KB.glob("*/*.md")}
    required_fields = {
        "id",
        "type",
        "tenant",
        "question",
        "expected_intent",
        "expected_doc_ids",
        "expected_evidence_keywords",
        "should_answer",
        "should_handoff",
        "risk_level",
    }

    for case in load_cases():
        assert required_fields <= set(case)
        assert case["tenant"] in {"tenant-a", "tenant-b", "tenant-internal"}
        assert case["risk_level"] in {"low", "medium", "high"}
        assert case["expected_doc_ids"]
        assert case["expected_evidence_keywords"]
        assert set(case["expected_doc_ids"]) <= doc_ids


def test_eval_distribution_covers_trace_risk_and_tenant_isolation_scenarios() -> None:
    cases = load_cases()
    distribution = Counter(case["type"] for case in cases)

    assert distribution["single_doc"] == 25
    assert distribution["multi_condition"] == 20
    assert distribution["multi_doc"] == 15
    assert distribution["keyword_exact"] == 15
    assert distribution["colloquial_rewrite"] == 15
    assert distribution["rewrite_drift"] == 10
    assert distribution["tenant_isolation"] == 10
    assert distribution["no_evidence_handoff"] == 10
    assert sum(1 for case in cases if case["should_handoff"]) >= 10
    assert sum(1 for case in cases if len(case["expected_doc_ids"]) > 1) >= 40
