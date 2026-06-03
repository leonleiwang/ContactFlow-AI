# 展示说明：Rerank Provider 测试验证 qwen3-rerank 关闭、缺少密钥和远程分数成功返回三类边界。
from app.models import KnowledgeChunk
from app.rag.rerank_provider import RerankProvider, RerankSettings
from app.rag.retrieval import HybridHit


# 构造候选证据：用最小 KnowledgeChunk 生成 HybridHit，聚焦测试 rerank Provider 行为。
def _hit(chunk_id: str, score: float) -> HybridHit:
    return HybridHit(
        chunk=KnowledgeChunk(chunk_id=chunk_id, tenant_id="tenant-a", title=chunk_id, text=f"{chunk_id} text"),
        score=score,
        vector_score=score,
        bm25_score=0.0,
        source_bonus=0.0,
        matched_by=("vector",),
    )


# 模型关闭：保持上游轻量排序结果，并在 trace 中标记 rerank_disabled。
def test_rerank_provider_disabled_keeps_lightweight_order() -> None:
    hits = [_hit("first", 0.9), _hit("second", 0.2)]
    provider = RerankProvider(
        RerankSettings(
            enabled=False,
            base_url="https://example.invalid/v1",
            api_key=None,
            model="qwen3-rerank",
            timeout_seconds=1,
        )
    )

    result = provider.rerank("refund", hits)

    assert result.mode == "lightweight"
    assert result.degraded_reason == "rerank_disabled"
    assert result.hits == hits


# 缺少密钥：即使开启 rerank，也必须降级到 lightweight，不能尝试远程调用。
def test_rerank_provider_missing_key_does_not_call_remote() -> None:
    hits = [_hit("first", 0.9)]
    provider = RerankProvider(
        RerankSettings(
            enabled=True,
            base_url="https://example.invalid/v1",
            api_key=None,
            model="qwen3-rerank",
            timeout_seconds=1,
        )
    )

    result = provider.rerank("refund", hits)

    assert result.mode == "lightweight"
    assert result.degraded_reason == "missing_api_key"


# 成功响应：使用远程 relevance_score 与本地分数融合，最高相关文档应排到第一位。
def test_rerank_provider_uses_remote_scores_when_available(monkeypatch) -> None:
    hits = [_hit("weak", 0.2), _hit("strong", 0.1)]
    provider = RerankProvider(
        RerankSettings(
            enabled=True,
            base_url="https://example.invalid/v1",
            api_key="test-key",
            model="qwen3-rerank",
            timeout_seconds=1,
        )
    )
    monkeypatch.setattr(provider, "_remote_scores", lambda query, items: [0.1, 0.95])

    result = provider.rerank("refund", hits)

    assert result.mode == "model"
    assert result.model_name == "qwen3-rerank"
    assert result.hits[0].chunk.chunk_id == "strong"
    assert "qwen3-rerank" in result.hits[0].matched_by
