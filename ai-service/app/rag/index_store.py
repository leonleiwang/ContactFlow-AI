from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.models import KnowledgeChunk


class JsonlChunkIndexStore:
    def write(self, chunks: Iterable[KnowledgeChunk], path: Path) -> dict[str, Any]:
        materialized = list(chunks)
        self._ensure_unique_chunk_ids(materialized)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as file:
            for chunk in materialized:
                file.write(json.dumps(self._to_payload(chunk), ensure_ascii=False, sort_keys=True))
                file.write("\n")
        return self.manifest(materialized, path)

    def read(self, path: Path) -> list[KnowledgeChunk]:
        chunks: list[KnowledgeChunk] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            chunks.append(self._from_payload(payload))
        self._ensure_unique_chunk_ids(chunks)
        return chunks

    def manifest(self, chunks: Iterable[KnowledgeChunk], path: Path) -> dict[str, Any]:
        materialized = list(chunks)
        tenants = sorted({chunk.tenant_id for chunk in materialized})
        doc_ids = sorted({chunk.doc_id for chunk in materialized if chunk.doc_id})
        return {
            "format": "contactflow-rag-chunks-jsonl",
            "version": "0.2.0",
            "path": path.as_posix(),
            "chunk_count": len(materialized),
            "doc_count": len(doc_ids),
            "tenants": tenants,
            "doc_ids": doc_ids,
        }

    @staticmethod
    def _to_payload(chunk: KnowledgeChunk) -> dict[str, Any]:
        payload = asdict(chunk)
        payload["tags"] = sorted(chunk.tags)
        payload["section_path"] = list(chunk.section_path)
        payload["acl_tags"] = sorted(chunk.acl_tags)
        return payload

    @staticmethod
    def _from_payload(payload: dict[str, Any]) -> KnowledgeChunk:
        return KnowledgeChunk(
            chunk_id=payload["chunk_id"],
            tenant_id=payload["tenant_id"],
            title=payload["title"],
            text=payload["text"],
            tags=set(payload.get("tags") or []),
            doc_id=payload.get("doc_id"),
            section_path=tuple(payload.get("section_path") or []),
            source_uri=payload.get("source_uri"),
            parent_id=payload.get("parent_id"),
            effective_from=payload.get("effective_from"),
            effective_to=payload.get("effective_to"),
            acl_tags=set(payload.get("acl_tags") or []),
            checksum=payload.get("checksum"),
        )

    @staticmethod
    def _ensure_unique_chunk_ids(chunks: list[KnowledgeChunk]) -> None:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for chunk in chunks:
            if chunk.chunk_id in seen:
                duplicates.add(chunk.chunk_id)
            seen.add(chunk.chunk_id)
        if duplicates:
            joined = ", ".join(sorted(duplicates))
            raise ValueError(f"Duplicate chunk ids in index: {joined}")
