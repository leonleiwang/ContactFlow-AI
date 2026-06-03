# 展示说明：LLM Provider 测试验证关闭模型、缺少密钥和 OpenAI-compatible 成功响应三条关键边界。
import pytest

from app.llm_provider import LlmProvider, LlmSettings


# 模型关闭：默认本地演示不调用外部 LLM，直接返回模板兜底结果。
def test_llm_provider_uses_template_when_disabled() -> None:
    provider = LlmProvider(
        LlmSettings(
            enabled=False,
            base_url="https://example.invalid/v1",
            api_key=None,
            model="qwen3-max",
            fallback_model="qwen-plus",
            timeout_seconds=1,
            max_retries=0,
        )
    )

    result = provider.generate(
        ticket_title="退款咨询",
        customer_message="我想退款",
        intent="refund",
        route="rag",
        sla_risk="LOW",
        template_summary="模板摘要",
        template_reply="模板回复",
        citations=[],
    )

    assert result.mode == "template_fallback"
    assert result.degraded_reason == "llm_disabled"
    assert result.summary == "模板摘要"
    assert result.suggested_reply == "模板回复"
    assert result.estimated_cost_usd == 0.0


# 缺少密钥：即使开启 LLM_ENABLED，也不能发起远程请求，应明确返回 missing_api_key。
def test_llm_provider_missing_key_does_not_call_remote() -> None:
    provider = LlmProvider(
        LlmSettings(
            enabled=True,
            base_url="https://example.invalid/v1",
            api_key=None,
            model="qwen3-max",
            fallback_model="qwen-plus",
            timeout_seconds=1,
            max_retries=0,
        )
    )

    result = provider.generate(
        ticket_title="投诉",
        customer_message="我要投诉",
        intent="complaint",
        route="handoff",
        sla_risk="HIGH",
        template_summary="高风险摘要",
        template_reply="转人工回复",
        citations=[],
    )

    assert result.mode == "template_fallback"
    assert result.degraded_reason == "missing_api_key"


# 成功响应：兼容 OpenAI Chat Completions 的 JSON 字符串内容，并记录实际模型名称。
def test_llm_provider_parses_openai_compatible_json_response(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = LlmProvider(
        LlmSettings(
            enabled=True,
            base_url="https://example.invalid/v1",
            api_key="test-key",
            model="qwen3-max",
            fallback_model=None,
            timeout_seconds=1,
            max_retries=0,
        )
    )

    monkeypatch.setattr(
        provider,
        "_chat_completion",
        lambda model, prompt: {
            "choices": [
                {
                    "message": {
                        "content": '{"summary":"LLM 摘要","suggested_reply":"LLM 回复"}',
                    }
                }
            ]
        },
    )

    result = provider.generate(
        ticket_title="物流延迟",
        customer_message="物流一直没更新",
        intent="delivery",
        route="rag",
        sla_risk="MEDIUM",
        template_summary="模板摘要",
        template_reply="模板回复",
        citations=[{"docId": "tenant-a/delivery_delay_sop.md"}],
    )

    assert result.mode == "llm"
    assert result.model_name == "qwen3-max"
    assert result.summary == "LLM 摘要"
    assert result.suggested_reply == "LLM 回复"
    assert result.degraded_reason is None
