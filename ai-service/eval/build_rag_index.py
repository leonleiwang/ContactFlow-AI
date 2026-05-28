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
    manifest = build_index()
    print("ContactFlow AI RAG Index v0.2")
    print(f"Chunks: {manifest['chunk_count']}")
    print(f"Docs: {manifest['doc_count']}")
    print(f"Tenants: {', '.join(manifest['tenants'])}")


if __name__ == "__main__":
    main()
