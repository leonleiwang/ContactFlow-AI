# 展示说明：Rerank Provider 抽象层，优先支持 qwen3-rerank，失败时降级到本地轻量重排序。
from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass

from app.rag.retrieval import HybridHit


@dataclass(frozen=True)
# 重排序结果：统一返回排序后的 hit、执行模式、模型名称和降级原因，直接进入 RAG trace。
class RerankResult:
    hits: list[HybridHit]
    mode: str
    model_name: str | None
    degraded_reason: str | None


@dataclass(frozen=True)
# 重排序配置：从环境变量读取模型开关、服务地址、密钥、模型名和超时时间。
class RerankSettings:
    enabled: bool
    base_url: str
    api_key: str | None
    model: str
    timeout_seconds: float

    # 环境变量装配：默认关闭远程 rerank，保证没有 API Key 时仍能使用本地 lightweight 排序。
    @classmethod
    def from_env(cls) -> "RerankSettings":
        return cls(
            enabled=os.getenv("RERANK_ENABLED", "false").lower() == "true",
            base_url=os.getenv("RERANK_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/"),
            api_key=os.getenv("DASHSCOPE_API_KEY") or os.getenv("RERANK_API_KEY") or os.getenv("LLM_API_KEY"),
            model=os.getenv("RERANK_MODEL", "qwen3-rerank"),
            timeout_seconds=max(float(os.getenv("RERANK_TIMEOUT_SECONDS", "3")), 0.5),
        )


# qwen3-rerank 接入层：只负责候选证据的二次排序，不参与租户过滤和风险决策。
class RerankProvider:
    # 初始化 Provider：支持测试注入配置，运行时默认读取 RERANK_* 与 DASHSCOPE_API_KEY。
    def __init__(self, settings: RerankSettings | None = None) -> None:
        self.settings = settings or RerankSettings.from_env()

    # 执行重排序：远程模型不可用时保留上游轻量排序结果，并记录明确的 degraded_reason。
    def rerank(self, query: str, hits: list[HybridHit]) -> RerankResult:
        if not hits:
            return RerankResult(hits=[], mode="empty", model_name=None, degraded_reason=None)
        if not self.settings.enabled:
            return RerankResult(hits=hits, mode="lightweight", model_name=None, degraded_reason="rerank_disabled")
        if not self.settings.api_key:
            return RerankResult(hits=hits, mode="lightweight", model_name=None, degraded_reason="missing_api_key")

        try:
            scores = self._remote_scores(query, hits)
            if len(scores) != len(hits):
                raise ValueError("rerank_score_count_mismatch")
            reranked = [
                HybridHit(
                    chunk=hit.chunk,
                    score=round((hit.score * 0.35) + (max(score, 0.0) * 0.65), 6),
                    vector_score=hit.vector_score,
                    bm25_score=hit.bm25_score,
                    source_bonus=hit.source_bonus,
                    matched_by=tuple(sorted(set(hit.matched_by) | {"qwen3-rerank"})),
                )
                for hit, score in zip(hits, scores)
            ]
            return RerankResult(
                hits=sorted(reranked, key=lambda item: item.score, reverse=True),
                mode="model",
                model_name=self.settings.model,
                degraded_reason=None,
            )
        except (TimeoutError, socket.timeout):
            return RerankResult(hits=hits, mode="lightweight", model_name=None, degraded_reason="rerank_timeout")
        except (urllib.error.URLError, urllib.error.HTTPError):
            return RerankResult(hits=hits, mode="lightweight", model_name=None, degraded_reason="rerank_http_error")
        except (ValueError, KeyError, json.JSONDecodeError):
            return RerankResult(hits=hits, mode="lightweight", model_name=None, degraded_reason="rerank_invalid_response")

    # 远程分数请求：按候选列表顺序发送文档，解析 qwen3-rerank 或兼容返回中的 relevance_score。
    def _remote_scores(self, query: str, hits: list[HybridHit]) -> list[float]:
        request = urllib.request.Request(
            f"{self.settings.base_url}/rerank",
            data=json.dumps(
                {
                    "model": self.settings.model,
                    "query": query,
                    "documents": [f"{hit.chunk.title}\n{hit.chunk.text}" for hit in hits],
                    "top_n": len(hits),
                },
                ensure_ascii=False,
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.settings.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))

        results = payload.get("results") or payload.get("output", {}).get("results") or []
        indexed_scores = {int(item["index"]): float(item["relevance_score"]) for item in results}
        return [indexed_scores.get(index, 0.0) for index in range(len(hits))]
