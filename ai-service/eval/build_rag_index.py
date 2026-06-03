# 展示说明：V0.3 ingestion 构建工具，把企业客服 Markdown 知识库切分为 JSONL 索引并落盘 manifest，支持命令行指定临时输出路径。
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rag.index_store import JsonlChunkIndexStore  # noqa: E402
from app.rag.query_engine import RagQueryEngine  # noqa: E402


# 构建索引：复用 RagQueryEngine 的 chunker 结果，生成 chunks.jsonl 和 manifest.json。
def build_index(
    dataset_root: Path | None = None,
    index_path: Path | None = None,
    manifest_path: Path | None = None,
) -> dict[str, object]:
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


# 命令行参数解析：允许发布前把索引写到临时文件，避免覆盖仓库内已提交的演示产物。
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build ContactFlow AI RAG JSONL index.")
    parser.add_argument("--dataset-root", type=Path, default=None)
    parser.add_argument("--chunks-output", type=Path, default=None)
    parser.add_argument("--manifest-output", type=Path, default=None)
    return parser.parse_args()


# 命令行入口：输出 chunk、文档和租户数量，方便本地演示 ingestion 结果。
def main() -> None:
    args = parse_args()
    manifest = build_index(dataset_root=args.dataset_root, index_path=args.chunks_output, manifest_path=args.manifest_output)
    print("ContactFlow AI RAG Index v0.3")
    print(f"Chunks: {manifest['chunk_count']}")
    print(f"Docs: {manifest['doc_count']}")
    print(f"Tenants: {', '.join(manifest['tenants'])}")


if __name__ == "__main__":
    main()
