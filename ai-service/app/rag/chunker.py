# 展示说明：V0.2 动态切分模块，按 Markdown 标题层级、段落和句子边界生成带父子关系的可追溯知识 chunk。
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
# 结构化段落块：保留标题、章节路径和正文，作为父子 chunk 的上游语义单元。
class ParsedBlock:
    title: str
    section_path: tuple[str, ...]
    text: str


class DynamicChunker:
    # 初始化 token budget 与 overlap，保证长文档切片既不超预算也能保留上下文连续性。
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
        # Markdown 切分主流程：把章节块转为带租户、doc_id、source_uri、parent_id 和 checksum 的索引单元。
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
        # 解析标题层级和自然段落，形成可展示的 section_path，便于 citations 定位到原文结构。
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
        # 基于中英文句末符号切句，让 chunk 边界尽量落在自然语义边界上。
        sentences = [part.strip() for part in SENTENCE_BOUNDARY_PATTERN.split(text) if part.strip()]
        if len(sentences) <= 1:
            return [text.strip()] if text.strip() else []
        return sentences

    def _window_sentences(self, sentences: list[str]) -> list[list[str]]:
        # 滑动窗口组装句子，按 max_tokens 控制召回颗粒度，并在窗口间保留 overlap。
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
        # 选择上一窗口尾部作为重叠上下文，减少跨句或跨段证据断裂。
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
