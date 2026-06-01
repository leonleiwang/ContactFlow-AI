# 展示说明：V0.2 ingestion 构建工具，把企业客服 Markdown 知识库切分为 JSONL 索引并落盘 manifest。
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rag.index_store import JsonlChunkIndexStore  # noqa: E402
from app.rag.query_engine import RagQueryEngine  # noqa: E402


def build_index(
    dataset_root: Path | None = None,
    index_path: Path | None = None,
    manifest_path: Path | None = None,
) -> dict[str, object]:
    # 构建索引：复用 RagQueryEngine 的 chunker 结果，生成 chunks.jsonl 和 manifest.json。
    engine = RagQueryEngine(dataset_root=dataset_root)
    root = dataset_root or engine.dataset_root
    target_index = index_path or root / "index" / "chunks.jsonl"
    target_manifest = manifest_path or root / "index" / "manifest.json"

    store = JsonlChunkIndexStore()
    manifest = store.write(engine.chunks, target_index)
    try:
        manifest["path"] = target_index.relative_to(root).as_posix()
    except ValueError:
        manifest["path"] = target_index.as_posix()
    target_manifest.parent.mkdir(parents=True, exist_ok=True)
    target_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    # 命令行入口：输出 chunk、文档和租户数量，方便本地演示 ingestion 结果。
    manifest = build_index()
    print("ContactFlow AI RAG Index v0.2")
    print(f"Chunks: {manifest['chunk_count']}")
    print(f"Docs: {manifest['doc_count']}")
    print(f"Tenants: {', '.join(manifest['tenants'])}")


if __name__ == "__main__":
    main()
