from pathlib import Path

from app.models import KnowledgeChunk
from app.rag.index_store import JsonlChunkIndexStore
from eval.build_rag_index import build_index
from eval.run_rag_eval import run_eval


def test_jsonl_chunk_index_round_trips_metadata(tmp_path: Path) -> None:
    store = JsonlChunkIndexStore()
    index_path = tmp_path / "chunks.jsonl"
    chunks = [
        KnowledgeChunk(
            chunk_id="tenant-a/refund_policy.md:chunk:0:0",
            tenant_id="tenant-a",
            title="退款规则",
            text="签收 7 天内且商品未使用，可以申请退款。",
            tags={"refund", "manual"},
            doc_id="tenant-a/refund_policy.md",
            section_path=("退款政策", "标准规则"),
            source_uri="dataset://contactflow_demo_kb_v0.2/tenant-a/refund_policy.md",
            parent_id="tenant-a/refund_policy.md:section:0",
            effective_from="2026-01-01",
            acl_tags={"support"},
            checksum="abc123",
        )
    ]

    manifest = store.write(chunks, index_path)
    loaded = store.read(index_path)

    assert manifest["chunk_count"] == 1
    assert manifest["doc_count"] == 1
    assert manifest["tenants"] == ["tenant-a"]
    assert loaded == chunks


def test_build_rag_index_writes_jsonl_and_manifest(tmp_path: Path) -> None:
    index_path = tmp_path / "index" / "chunks.jsonl"
    manifest_path = tmp_path / "index" / "manifest.json"

    manifest = build_index(index_path=index_path, manifest_path=manifest_path)

    assert index_path.exists()
    assert manifest_path.exists()
    assert manifest["chunk_count"] > 0
    assert {"tenant-a", "tenant-b", "tenant-internal"}.issubset(set(manifest["tenants"]))


def test_rag_eval_writes_operational_report(tmp_path: Path) -> None:
    report_path = tmp_path / "latest_report.json"

    report = run_eval(report_path=report_path, include_case_results=False)

    assert report_path.exists()
    assert report["summary"]["total_cases"] == 120
    assert report["summary"]["tenant_leak_count"] == 0
    assert "context_recall" in report["summary"]
    assert "handoff_accuracy" in report["summary"]
