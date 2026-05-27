from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable

from app.models import KnowledgeChunk
from app.rag.embedding import tokenize


HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")
SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[。！？!?\.])\s*")


@dataclass(frozen=True)
class ParsedBlock:
    title: str
    section_path: tuple[str, ...]
    text: str


class DynamicChunker:
    def __init__(self, max_tokens: int = 180, overlap_tokens: int = 100) -> None:
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if overlap_tokens < 0:
            raise ValueError("overlap_tokens cannot be negative")
        self.max_tokens = max_tokens
        self.overlap_tokens = min(overlap_tokens, max_tokens // 2)

    def split_markdown(
        self,
        content: str,
        *,
        tenant_id: str,
        doc_id: str,
        source_uri: str,
        acl_tags: Iterable[str] = (),
    ) -> list[KnowledgeChunk]:
        blocks = self._parse_blocks(content)
        chunks: list[KnowledgeChunk] = []
        for block_index, block in enumerate(blocks):
            windows = self._window_sentences(self._split_sentences(block.text))
            parent_id = f"{doc_id}:section:{block_index}"
            for window_index, window in enumerate(windows):
                text = " ".join(window).strip()
                if not text:
                    continue
                checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"{doc_id}:chunk:{block_index}:{window_index}",
                        tenant_id=tenant_id,
                        title=block.title,
                        text=text,
                        tags=set(acl_tags),
                        doc_id=doc_id,
                        section_path=block.section_path,
                        source_uri=source_uri,
                        parent_id=parent_id,
                        acl_tags=set(acl_tags),
                        checksum=checksum,
                    )
                )
        return chunks

    def _parse_blocks(self, content: str) -> list[ParsedBlock]:
        headings: list[str] = []
        current_lines: list[str] = []
        blocks: list[ParsedBlock] = []

        def flush() -> None:
            text = "\n".join(line for line in current_lines if line.strip()).strip()
            if not text:
                current_lines.clear()
                return
            title = headings[-1] if headings else "root"
            blocks.append(ParsedBlock(title=title, section_path=tuple(headings), text=text))
            current_lines.clear()

        for raw_line in content.splitlines():
            line = raw_line.rstrip()
            heading = HEADING_PATTERN.match(line)
            if heading:
                flush()
                level = len(heading.group(1))
                title = heading.group(2).strip()
                headings = headings[: level - 1] + [title]
                continue
            if not line.strip():
                flush()
                continue
            current_lines.append(line)
        flush()
        return blocks

    def _split_sentences(self, text: str) -> list[str]:
        sentences = [part.strip() for part in SENTENCE_BOUNDARY_PATTERN.split(text) if part.strip()]
        if len(sentences) <= 1:
            return [text.strip()] if text.strip() else []
        return sentences

    def _window_sentences(self, sentences: list[str]) -> list[list[str]]:
        windows: list[list[str]] = []
        current: list[str] = []
        current_tokens = 0
        for sentence in sentences:
            sentence_tokens = max(len(tokenize(sentence)), 1)
            if current and current_tokens + sentence_tokens > self.max_tokens:
                windows.append(current)
                current = self._overlap_tail(current)
                current_tokens = sum(max(len(tokenize(item)), 1) for item in current)
            current.append(sentence)
            current_tokens += sentence_tokens
        if current:
            windows.append(current)
        return windows

    def _overlap_tail(self, sentences: list[str]) -> list[str]:
        if self.overlap_tokens == 0:
            return []
        selected: list[str] = []
        count = 0
        for sentence in reversed(sentences):
            sentence_tokens = max(len(tokenize(sentence)), 1)
            if selected and count + sentence_tokens > self.overlap_tokens:
                break
            selected.append(sentence)
            count += sentence_tokens
        return list(reversed(selected))
